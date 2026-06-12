import 'dart:async';
import 'dart:io';
import 'dart:ui';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:permission_handler/permission_handler.dart';

import '../models/register_scan_step.dart';
import '../utils/camera_input_image.dart';

enum ScanPhase { idle, loading, scanning, capturing, submitting, done, error }

class FaceFrameMetrics {
  const FaceFrameMetrics({
    required this.centerX,
    required this.centerY,
    required this.faceWidth,
    required this.faceHeight,
    required this.headEulerY,
    required this.frameWidth,
    required this.frameHeight,
    required this.meshPoints,
  });

  final double centerX;
  final double centerY;
  final double faceWidth;
  final double faceHeight;
  final double headEulerY;
  final double frameWidth;
  final double frameHeight;
  final List<Offset> meshPoints;
}

class LiveFaceRegisterController extends ChangeNotifier {
  LiveFaceRegisterController();

  static const requiredStableFrames = 12;

  CameraController? cameraController;
  FaceDetector? _detector;
  ScanPhase phase = ScanPhase.idle;
  String statusTitle = 'Preparando';
  String statusHint = 'Iniciando camara...';
  int stepIndex = 0;
  int stableFrames = 0;
  bool aligned = false;
  bool poseOk = false;
  FaceFrameMetrics? latestMetrics;
  InputImageRotation? imageRotation;
  Size imageSize = Size.zero;
  final Map<String, File> captures = {};
  String? errorMessage;
  int _frameSkip = 0;
  bool _processingFrame = false;
  bool _capturingStep = false;
  DeviceOrientation _deviceOrientation = DeviceOrientation.portraitUp;

  RegisterScanStep get currentStep => registerScanSteps[stepIndex];
  bool get isComplete => registerScanSteps.every((s) => captures.containsKey(s.key));

  Future<void> initialize() async {
    if (phase == ScanPhase.loading || phase == ScanPhase.scanning) return;
    phase = ScanPhase.loading;
    statusTitle = 'Preparando escaneo';
    statusHint = 'Solicitando permisos de camara';
    errorMessage = null;
    notifyListeners();

    final permission = await Permission.camera.request();
    if (!permission.isGranted) {
      _setError('Se necesita permiso de camara para registrar tu rostro.');
      return;
    }

    try {
      final cameras = await availableCameras();
      final front = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      _detector = FaceDetector(
        options: FaceDetectorOptions(
          enableContours: true,
          enableLandmarks: true,
          performanceMode: FaceDetectorMode.fast,
          minFaceSize: 0.12,
        ),
      );

      cameraController = CameraController(
        front,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: Platform.isAndroid
            ? ImageFormatGroup.nv21
            : ImageFormatGroup.bgra8888,
      );

      await cameraController!.initialize();
      imageRotation = rotationFromCamera(front, _deviceOrientation);
      final preview = cameraController!.value.previewSize;
      if (preview != null) {
        imageSize = Size(preview.height, preview.width);
      }

      await cameraController!.startImageStream(_onCameraFrame);

      phase = ScanPhase.scanning;
      statusTitle = 'Escaneo iniciado';
      statusHint = currentStep.prompt;
      notifyListeners();
    } catch (error) {
      _setError('No se pudo iniciar la camara: $error');
    }
  }

  void updateDeviceOrientation(DeviceOrientation orientation) {
    _deviceOrientation = orientation;
    final camera = cameraController?.description;
    if (camera != null) {
      imageRotation = rotationFromCamera(camera, orientation);
    }
  }

  Future<void> _onCameraFrame(CameraImage image) async {
    if (phase != ScanPhase.scanning || _capturingStep || _detector == null) {
      return;
    }

    _frameSkip += 1;
    if (_frameSkip % 2 != 0 || _processingFrame) return;
    _processingFrame = true;

    try {
      final camera = cameraController!.description;
      final input = inputImageFromCameraImage(
        image: image,
        camera: camera,
        deviceOrientation: _deviceOrientation,
      );
      if (input == null) return;

      imageSize = Size(image.width.toDouble(), image.height.toDouble());
      imageRotation = input.metadata?.rotation ?? imageRotation;

      final faces = await _detector!.processImage(input);
      if (faces.isEmpty) {
        stableFrames = 0;
        aligned = false;
        poseOk = false;
        latestMetrics = null;
        statusHint = 'Coloca tu rostro dentro del circulo';
        notifyListeners();
        return;
      }

      final face = faces.first;
      final metrics = _metricsFromFace(face, image.width.toDouble(), image.height.toDouble());
      latestMetrics = metrics;
      aligned = _isFaceAligned(metrics);
      poseOk = currentStep.matchesPose(metrics.headEulerY);

      if (aligned && poseOk) {
        stableFrames += 1;
        final remaining = (requiredStableFrames - stableFrames).clamp(0, 99);
        statusHint = remaining > 0
            ? 'Mantente quieto... $remaining'
            : 'Capturando...';
        if (stableFrames >= requiredStableFrames) {
          await _captureCurrentStep();
        }
      } else {
        stableFrames = 0;
        statusHint = aligned ? currentStep.prompt : 'Centra tu rostro en el circulo';
      }
      notifyListeners();
    } catch (_) {
      // Ignorar frames fallidos para mantener fluidez.
    } finally {
      _processingFrame = false;
    }
  }

  FaceFrameMetrics _metricsFromFace(Face face, double width, double height) {
    final box = face.boundingBox;
    final centerX = box.left + box.width / 2;
    final centerY = box.top + box.height / 2;
    final points = <Offset>[];

    for (final contour in face.contours?.values ?? const Iterable<FaceContour?>.empty()) {
      if (contour == null) continue;
      for (final point in contour.points) {
        points.add(Offset(point.x.toDouble(), point.y.toDouble()));
      }
    }

    if (points.isEmpty) {
      for (final landmark in face.landmarks.values) {
        final pos = landmark?.position;
        if (pos != null) {
          points.add(Offset(pos.x.toDouble(), pos.y.toDouble()));
        }
      }
    }

    return FaceFrameMetrics(
      centerX: centerX,
      centerY: centerY,
      faceWidth: box.width,
      faceHeight: box.height,
      headEulerY: face.headEulerAngleY ?? 0,
      frameWidth: width,
      frameHeight: height,
      meshPoints: points,
    );
  }

  bool _isFaceAligned(FaceFrameMetrics metrics) {
    final frameCenterX = metrics.frameWidth / 2;
    final frameCenterY = metrics.frameHeight / 2;
    final frameSize = metrics.frameWidth < metrics.frameHeight
        ? metrics.frameWidth
        : metrics.frameHeight;
    final dx = (metrics.centerX - frameCenterX).abs();
    final dy = (metrics.centerY - frameCenterY).abs();
    final centerTolerance = frameSize * 0.12;
    final sizeRatio = metrics.faceWidth / frameSize;
    return dx <= centerTolerance &&
        dy <= centerTolerance &&
        sizeRatio >= 0.26 &&
        sizeRatio <= 0.64;
  }

  Future<void> _captureCurrentStep() async {
    if (_capturingStep || cameraController == null) return;
    _capturingStep = true;
    phase = ScanPhase.capturing;
    statusTitle = 'Capturando ${currentStep.label}';
    statusHint = 'Un momento...';
    notifyListeners();

    try {
      await cameraController!.stopImageStream();
      final file = await cameraController!.takePicture();
      final capturedStep = currentStep;
      captures[capturedStep.key] = File(file.path);
      stableFrames = 0;

      if (stepIndex < registerScanSteps.length - 1) {
        stepIndex += 1;
        phase = ScanPhase.scanning;
        statusTitle = '${capturedStep.label} capturada';
        statusHint = currentStep.prompt;
        await cameraController!.startImageStream(_onCameraFrame);
      } else {
        phase = ScanPhase.done;
        statusTitle = 'Escaneo completo';
        statusHint = 'Las 3 poses fueron capturadas';
      }
      notifyListeners();
    } catch (error) {
      _setError('Error al capturar foto: $error');
    } finally {
      _capturingStep = false;
    }
  }

  Future<void> resetAndRestart() async {
    await _disposeResources();
    stepIndex = 0;
    stableFrames = 0;
    aligned = false;
    poseOk = false;
    latestMetrics = null;
    captures.clear();
    errorMessage = null;
    phase = ScanPhase.idle;
    notifyListeners();
    await initialize();
  }

  void markSubmitting() {
    phase = ScanPhase.submitting;
    statusTitle = 'Guardando perfil';
    statusHint = 'Subiendo capturas al servidor...';
    notifyListeners();
  }

  void _setError(String message) {
    phase = ScanPhase.error;
    errorMessage = message;
    statusTitle = 'Error';
    statusHint = message;
    notifyListeners();
  }

  @override
  void dispose() {
    unawaited(_disposeResources());
    super.dispose();
  }

  Future<void> _disposeResources() async {
    final controller = cameraController;
    cameraController = null;
    if (controller != null) {
      if (controller.value.isStreamingImages) {
        await controller.stopImageStream();
      }
      await controller.dispose();
    }
    await _detector?.close();
    _detector = null;
  }
}
