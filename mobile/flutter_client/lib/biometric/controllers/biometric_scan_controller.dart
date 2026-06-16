import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../models/register_scan_step.dart';
import '../../utils/camera_input_image.dart';
import '../../utils/camera_overlay_mapper.dart';
import '../config/biometric_config.dart';
import '../models/biometric_scan_phase.dart';
import '../models/biometric_transition_state.dart';
import '../models/biometric_ui_state.dart';
import '../models/face_scan_state.dart';
import '../models/face_quality_issue.dart';
import '../models/overlay_geometry.dart';
import '../services/face_detection_service.dart';
import '../services/face_quality_analyzer.dart';
import '../services/frame_throttler.dart';
import '../services/stability_tracker.dart';
import '../widgets/capture_transition_layer.dart' show biometricCaptureHaptic;

/// Controlador del flujo biometrico de 3 pasos.
typedef FaceScanController = BiometricScanController;

class BiometricScanController {
  BiometricScanController();

  final overlayState = ValueNotifier<FaceScanState>(FaceScanState.initial);
  final uiState = ValueNotifier<BiometricUiState>(const BiometricUiState());
  final transitionState = ValueNotifier<BiometricTransitionState>(
    BiometricTransitionState.idle,
  );

  final FaceDetectionService _detection = FaceDetectionService();
  final FaceQualityAnalyzer _quality = const FaceQualityAnalyzer();
  final FrameThrottler _throttler =
      FrameThrottler(intervalMs: BiometricConfig.frameIntervalMs);
  final StabilityTracker _stability = StabilityTracker();

  void _resetStabilityForStep(String stepKey) {
    _stability
      ..requiredGoodFrames = BiometricConfig.stabilityFramesFor(stepKey)
      ..badFrameDecay = BiometricConfig.stabilityBadFrameDecay
      ..reset();
  }

  CameraController? cameraController;
  InputImageRotation? imageRotation;
  Size imageSize = Size.zero;
  Size canvasSize = Size.zero;
  GuideOvalLayout? _targetLayout;

  double _sweepAngle = 0;
  bool _isProcessing = false;
  bool _capturingStep = false;
  DeviceOrientation _deviceOrientation = DeviceOrientation.portraitUp;

  RegisterScanStep get currentStep => registerScanSteps[uiState.value.stepIndex];
  bool get isComplete =>
      registerScanSteps.every((s) => uiState.value.captures.containsKey(s.key));

  Map<String, File> get captures => uiState.value.captures;
  BiometricScanPhase get phase => uiState.value.phase;

  Future<void> initialize() async {
    final current = uiState.value;
    if (current.phase == BiometricScanPhase.loading ||
        current.phase == BiometricScanPhase.scanning) {
      return;
    }

    _updateUi(
      current.copyWith(
        phase: BiometricScanPhase.loading,
        statusTitle: 'Preparando',
        statusHint: 'Iniciando camara',
        clearError: true,
        clearWarning: true,
      ),
    );

    final permission = await Permission.camera.request();
    if (!permission.isGranted) {
      _setError('Se necesita permiso de camara para registrar tu rostro.');
      return;
    }

    try {
      await _detection.init();

      final cameras = await availableCameras();
      final front = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
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

      _resetStabilityForStep(registerScanSteps.first.key);
      _updateUi(
        uiState.value.copyWith(
          phase: BiometricScanPhase.scanning,
          statusTitle: currentStep.prompt,
          statusHint: 'Centra tu rostro',
        ),
      );
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

  void updateLayout({
    required Size canvas,
    required double topReserved,
    required double bottomReserved,
  }) {
    canvasSize = canvas;
    _targetLayout = GuideOvalLayout(
      size: canvas,
      topReserved: topReserved,
      bottomReserved: bottomReserved,
    );
    final target = _targetLayout!.guide;
    final next = overlayState.value.copyWith(
      targetOval: target,
      displayOval: target,
    );
    _setOverlayIfChanged(next);
  }

  CameraOverlayMapper? get _mapper {
    final camera = cameraController?.description;
    final rotation = imageRotation;
    if (camera == null || rotation == null || canvasSize.width <= 0) {
      return null;
    }
    return CameraOverlayMapper(
      canvasSize: canvasSize,
      imageSize: imageSize,
      rotation: rotation,
      lensDirection: camera.lensDirection,
    );
  }

  Future<void> _onCameraFrame(CameraImage image) async {
    if (uiState.value.phase != BiometricScanPhase.scanning ||
        _capturingStep ||
        _isProcessing ||
        !_throttler.shouldProcess()) {
      return;
    }

    _isProcessing = true;
    _throttler.markStarted();

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

      final faces = await _detection.detect(input);
      final mapper = _mapper;
      final target = _targetLayout?.guide ?? overlayState.value.displayOval;

      if (mapper == null || !mapper.isValid) return;

      FaceQualityIssue issue = FaceQualityIssue.noFace;
      List<Offset> debugLandmarks = const [];
      var hasFace = false;

      if (faces.isNotEmpty) {
        hasFace = true;
        final face = faces.first;
        final mapped = mapper.mapFaceRect(
          left: face.boundingBox.left,
          top: face.boundingBox.top,
          width: face.boundingBox.width,
          height: face.boundingBox.height,
        );

        if (BiometricConfig.debugMode) {
          debugLandmarks = _extractLandmarks(face, mapper);
        }

        issue = _quality.analyze(
          faces: faces,
          imageWidth: image.width.toDouble(),
          step: currentStep,
          mappedCenter: mapped.center,
          guide: target,
          lensDirection: camera.lensDirection,
        );
      }

      final isGood = issue == FaceQualityIssue.none;
      final ready = _stability.register(isGood);

      final visualState = _visualFor(issue, isGood, hasFace);
      if (visualState == OverlayVisualState.ready) {
        final t = DateTime.now().millisecondsSinceEpoch % 2000;
        _sweepAngle = (t / 2000) * math.pi * 2;
      }

      final overlayNext = FaceScanState(
        displayOval: target,
        targetOval: target,
        debugLandmarks: debugLandmarks,
        visualState: visualState,
        sweepAngle: _sweepAngle,
        lockProgress: _stability.progress,
        hasFace: hasFace,
      );
      _setOverlayIfChanged(overlayNext);

      _maybeUpdateUi(
        issue: issue,
        isGood: isGood,
        step: currentStep,
      );

      if (ready) await _captureCurrentStep();
    } catch (_) {
      // Frame descartado.
    } finally {
      _isProcessing = false;
      _throttler.markFinished();
    }
  }

  void _setOverlayIfChanged(FaceScanState next) {
    if (!overlayState.value.visuallyEquals(next)) {
      overlayState.value = next;
    }
  }

  void _maybeUpdateUi({
    required FaceQualityIssue issue,
    required bool isGood,
    required RegisterScanStep step,
  }) {
    final progress = _stability.progress;
    final title = step.prompt;
    final hint = _resolveHint(issue: issue, isGood: isGood, step: step);
    final warning = !isGood && _quality.isSecondaryWarning(issue)
        ? _quality.hintFor(issue, step)
        : null;

    final prev = uiState.value;
    if (prev.statusTitle == title &&
        prev.statusHint == hint &&
        prev.warningHint == warning &&
        (prev.stabilityProgress - progress).abs() < 0.02) {
      return;
    }

    uiState.value = prev.copyWith(
      statusTitle: title,
      statusHint: hint,
      warningHint: warning,
      clearWarning: warning == null,
      stabilityProgress: progress,
    );
  }

  String _resolveHint({
    required FaceQualityIssue issue,
    required bool isGood,
    required RegisterScanStep step,
  }) {
    if (isGood) {
      if (_stability.progress >= 0.95) return 'Capturando...';
      return 'Perfecto — no te muevas';
    }
    return _quality.hintFor(issue, step);
  }

  OverlayVisualState _visualFor(
    FaceQualityIssue issue,
    bool isGood,
    bool hasFace,
  ) {
    if (!hasFace) return OverlayVisualState.searching;
    if (isGood) {
      return _stability.progress >= 0.5
          ? OverlayVisualState.ready
          : OverlayVisualState.adjusting;
    }
    if (issue == FaceQualityIssue.offCenter ||
        issue == FaceQualityIssue.badPose ||
        issue == FaceQualityIssue.tooFar ||
        issue == FaceQualityIssue.tooClose) {
      return OverlayVisualState.warning;
    }
    return OverlayVisualState.warning;
  }

  List<Offset> _extractLandmarks(Face face, CameraOverlayMapper mapper) {
    const keys = [
      FaceLandmarkType.leftEye,
      FaceLandmarkType.rightEye,
      FaceLandmarkType.noseBase,
    ];
    return [
      for (final key in keys)
        if (face.landmarks[key]?.position case final pos?)
          mapper.mapPoint(pos.x.toDouble(), pos.y.toDouble()),
    ];
  }

  void _emitTransition(BiometricTransitionKind kind, {String? stepKey}) {
    transitionState.value = transitionState.value.next(
      kind: kind,
      stepKey: stepKey,
    );
    biometricCaptureHaptic(kind);
  }

  Future<void> _captureCurrentStep() async {
    if (_capturingStep || cameraController == null) return;
    _capturingStep = true;
    _stability.reset();

    final capturedStep = currentStep;

    _setOverlayIfChanged(
      overlayState.value.copyWith(
        capturePulse: 1,
        visualState: OverlayVisualState.ready,
        debugLandmarks: const [],
      ),
    );

    _emitTransition(BiometricTransitionKind.flash);
    await Future<void>.delayed(const Duration(milliseconds: 90));

    _updateUi(
      uiState.value.copyWith(
        phase: BiometricScanPhase.capturing,
        statusTitle: capturedStep.prompt,
        statusHint: 'Capturando',
        clearWarning: true,
        stabilityProgress: 0,
      ),
    );

    try {
      await cameraController!.stopImageStream();
      final file = await cameraController!.takePicture();
      final updatedCaptures = Map<String, File>.from(uiState.value.captures)
        ..[capturedStep.key] = File(file.path);

      final isLast = uiState.value.stepIndex >= registerScanSteps.length - 1;

      _emitTransition(
        isLast
            ? BiometricTransitionKind.allComplete
            : BiometricTransitionKind.stepSuccess,
        stepKey: capturedStep.key,
      );

      _setOverlayIfChanged(
        overlayState.value.copyWith(capturePulse: 0, lockProgress: 0),
      );

      _updateUi(
        uiState.value.copyWith(
          captures: updatedCaptures,
          statusTitle: isLast
              ? 'Listo'
              : registerScanSteps[uiState.value.stepIndex + 1].prompt,
          statusHint: isLast ? 'Escaneo completo' : 'Siguiente pose',
        ),
      );

      await Future<void>.delayed(
        Duration(milliseconds: isLast ? 680 : 480),
      );

      if (!isLast) {
        final nextIndex = uiState.value.stepIndex + 1;
        final nextStep = registerScanSteps[nextIndex];
        _resetStabilityForStep(nextStep.key);
        _emitTransition(BiometricTransitionKind.idle);
        _updateUi(
          uiState.value.copyWith(
            phase: BiometricScanPhase.scanning,
            statusTitle: nextStep.prompt,
            statusHint: 'Centra tu rostro',
            stepIndex: nextIndex,
            stabilityProgress: 0,
            clearWarning: true,
          ),
        );
        final target = _targetLayout?.guide ?? overlayState.value.displayOval;
        _setOverlayIfChanged(
          FaceScanState(
            displayOval: target,
            targetOval: target,
            visualState: OverlayVisualState.searching,
            hasFace: false,
          ),
        );
        await Future<void>.delayed(const Duration(milliseconds: 160));
        await cameraController!.startImageStream(_onCameraFrame);
      } else {
        _emitTransition(BiometricTransitionKind.idle);
        await releaseCamera();
        _updateUi(
          uiState.value.copyWith(
            phase: BiometricScanPhase.done,
            statusTitle: 'Listo',
            statusHint: 'Escaneo completo',
          ),
        );
      }
    } catch (error) {
      _emitTransition(BiometricTransitionKind.idle);
      _setOverlayIfChanged(overlayState.value.copyWith(capturePulse: 0));
      _setError('Error al capturar foto: $error');
    } finally {
      _capturingStep = false;
    }
  }

  Future<void> resetAndRestart() async {
    await disposeResources();
    _resetStabilityForStep(registerScanSteps.first.key);
    uiState.value = const BiometricUiState();
    overlayState.value = FaceScanState.initial;
    transitionState.value = BiometricTransitionState.idle;
    await initialize();
  }

  /// Apaga camara y detector tras las 3 capturas (ahorra bateria durante subida).
  Future<void> releaseCamera() async {
    final controller = cameraController;
    cameraController = null;
    if (controller != null) {
      try {
        if (controller.value.isStreamingImages) {
          await controller.stopImageStream();
        }
      } catch (_) {}
      try {
        await controller.dispose();
      } catch (_) {}
    }
    try {
      await _detection.dispose();
    } catch (_) {}
  }

  void markSubmitting({String? hint, String? title}) {
    _updateUi(
      uiState.value.copyWith(
        phase: BiometricScanPhase.submitting,
        statusTitle: title ?? 'Guardando perfil',
        statusHint: hint ?? 'Subiendo al servidor',
        clearWarning: true,
      ),
    );
  }

  void setExternalError(String message, {String title = 'Error'}) {
    _setError(message, title: title);
  }

  void _setError(String message, {String title = 'Error'}) {
    _updateUi(
      uiState.value.copyWith(
        phase: BiometricScanPhase.error,
        statusTitle: title,
        statusHint: message,
        errorMessage: message,
        clearWarning: true,
      ),
    );
  }

  void _updateUi(BiometricUiState next) => uiState.value = next;

  Future<void> dispose() async => disposeResources();

  Future<void> disposeResources() async {
    final controller = cameraController;
    cameraController = null;
    if (controller != null) {
      if (controller.value.isStreamingImages) {
        await controller.stopImageStream();
      }
      await controller.dispose();
    }
    await _detection.dispose();
  }
}
