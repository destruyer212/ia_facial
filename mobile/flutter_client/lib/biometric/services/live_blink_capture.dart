import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

import '../../utils/camera_input_image.dart';
import 'frame_throttler.dart';

/// Detecta parpadeo en vivo con ML Kit y captura al cerrar los ojos.
class LiveBlinkCapture {
  LiveBlinkCapture() : _throttler = FrameThrottler(intervalMs: 120);

  FaceDetector? _detector;
  final FrameThrottler _throttler;

  static const double defaultEyeOpenMin = 0.52;
  static const double defaultEyeClosedMax = 0.45;
  static const double defaultEyeDropMin = 0.20;
  static const int openFramesRequired = 5;

  Future<void> _ensureDetector() async {
    if (_detector != null) return;
    _detector = FaceDetector(
      options: FaceDetectorOptions(
        enableContours: false,
        enableLandmarks: false,
        enableClassification: true,
        performanceMode: FaceDetectorMode.accurate,
        minFaceSize: 0.08,
      ),
    );
  }

  Future<File> captureOnBlink({
    required CameraController controller,
    required void Function(String hint) onHint,
    DeviceOrientation deviceOrientation = DeviceOrientation.portraitUp,
    Duration timeout = const Duration(seconds: 14),
    double eyeOpenMin = defaultEyeOpenMin,
    double eyeClosedMax = defaultEyeClosedMax,
    double eyeDropMin = defaultEyeDropMin,
  }) async {
    await _ensureDetector();

    if (controller.value.isStreamingImages) {
      await controller.stopImageStream();
    }

    final completer = Completer<File>();
    final timeoutTimer = Timer(timeout, () {
      if (!completer.isCompleted) {
        completer.completeError(
          TimeoutException(
            'No se detecto parpadeo a tiempo. Mira de frente y parpadea de forma natural.',
          ),
        );
      }
    });

    var openFrames = 0;
    var baselineOpen = 0.0;
    var processing = false;
    var streamStopped = false;

    Future<void> stopStream() async {
      if (streamStopped) return;
      streamStopped = true;
      if (controller.value.isStreamingImages) {
        try {
          await controller.stopImageStream();
        } catch (_) {}
      }
    }

    onHint('Detectando parpadeo en vivo...');
    await Future<void>.delayed(const Duration(milliseconds: 350));

    try {
      await controller.startImageStream((image) async {
        if (completer.isCompleted || processing || streamStopped) return;
        if (!_throttler.shouldProcess()) return;

        processing = true;
        _throttler.markStarted();
        try {
          final input = inputImageFromCameraImage(
            image: image,
            camera: controller.description,
            deviceOrientation: deviceOrientation,
          );
          if (input == null) return;

          final faces = await _detector!.processImage(input);
          if (faces.isEmpty) {
            onHint('Centra tu rostro en la camara');
            openFrames = 0;
            baselineOpen = 0;
            return;
          }

          final score = _eyeOpenScore(faces.first);
          if (score == null) return;

          if (openFrames < openFramesRequired) {
            if (score >= eyeOpenMin) {
              openFrames += 1;
              baselineOpen = baselineOpen == 0
                  ? score
                  : (score * 0.35 + baselineOpen * 0.65).clamp(0.0, 1.0);
              if (score > baselineOpen) baselineOpen = score;
              onHint('Listo — parpadea de forma natural');
            } else {
              openFrames = openFrames > 0 ? openFrames - 1 : 0;
              onHint('Abre los ojos y mira a la camara');
            }
            return;
          }

          final drop = baselineOpen - score;
          final eyesClosed = score <= eyeClosedMax || drop >= eyeDropMin;
          if (!eyesClosed) {
            onHint('Te estamos mirando — parpadea cuando quieras');
            if (score > baselineOpen * 0.92) {
              baselineOpen = (score * 0.25 + baselineOpen * 0.75).clamp(0.0, 1.0);
            }
            return;
          }

          onHint('Parpadeo detectado — capturando...');
          await stopStream();
          final picture = await controller.takePicture();
          if (!completer.isCompleted) {
            completer.complete(File(picture.path));
          }
        } catch (error) {
          if (!completer.isCompleted) {
            completer.completeError(error);
          }
        } finally {
          processing = false;
          _throttler.markFinished();
        }
      });

      return await completer.future;
    } finally {
      timeoutTimer.cancel();
      await stopStream();
    }
  }

  /// Respaldo: rafaga y elige la foto con ojos mas cerrados.
  Future<File> captureBurstPickClosed({
    required CameraController controller,
    required void Function(String hint) onHint,
    int count = 8,
    Duration interval = const Duration(milliseconds: 110),
  }) async {
    await _ensureDetector();
    onHint('Reintento: parpadea ahora...');
    await Future<void>.delayed(const Duration(milliseconds: 400));

    File? bestFile;
    var lowestScore = double.infinity;

    for (var index = 0; index < count; index++) {
      if (controller.value.isStreamingImages) {
        try {
          await controller.stopImageStream();
        } catch (_) {}
      }

      final picture = await controller.takePicture();
      final file = File(picture.path);
      final score = await _scoreSavedPhoto(file);
      final effective = score ?? 1.0;
      if (effective <= lowestScore) {
        lowestScore = effective;
        bestFile = file;
      }
      if (index < count - 1) {
        await Future<void>.delayed(interval);
      }
    }

    if (bestFile != null) return bestFile;
    final picture = await controller.takePicture();
    return File(picture.path);
  }

  Future<double?> _scoreSavedPhoto(File file) async {
    try {
      final faces = await _detector!.processImage(InputImage.fromFilePath(file.path));
      if (faces.isEmpty) return null;
      return _eyeOpenScore(faces.first);
    } catch (_) {
      return null;
    }
  }

  double? _eyeOpenScore(Face face) {
    final left = face.leftEyeOpenProbability;
    final right = face.rightEyeOpenProbability;
    if (left == null || right == null) return null;
    return (left + right) / 2;
  }

  Future<void> dispose() async {
    await _detector?.close();
    _detector = null;
  }
}
