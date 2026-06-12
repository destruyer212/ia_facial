import 'dart:ui';

import 'package:camera/camera.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

/// Mapeo buffer NV21/BGRA -> canvas. Basado en google_ml_kit_flutter face_detector.
class CameraOverlayMapper {
  const CameraOverlayMapper({
    required this.canvasSize,
    required this.imageSize,
    required this.rotation,
    required this.lensDirection,
  });

  final Size canvasSize;
  final Size imageSize;
  final InputImageRotation rotation;
  final CameraLensDirection lensDirection;

  bool get isValid => canvasSize.width > 0 && imageSize.width > 0;

  Offset mapPoint(double x, double y) {
    return Offset(_translateX(x, y), _translateY(y));
  }

  Offset mapOffset(Offset point) => mapPoint(point.dx, point.dy);

  double _translateX(double x, double y) {
    switch (rotation) {
      case InputImageRotation.rotation90deg:
        return y * canvasSize.width / imageSize.height;
      case InputImageRotation.rotation270deg:
        return canvasSize.width - x * canvasSize.width / imageSize.height;
      case InputImageRotation.rotation0deg:
        return lensDirection == CameraLensDirection.front
            ? canvasSize.width - x * canvasSize.width / imageSize.width
            : x * canvasSize.width / imageSize.width;
      case InputImageRotation.rotation180deg:
        return lensDirection == CameraLensDirection.front
            ? x * canvasSize.width / imageSize.width
            : canvasSize.width - x * canvasSize.width / imageSize.width;
    }
  }

  double _translateY(double y) {
    switch (rotation) {
      case InputImageRotation.rotation90deg:
      case InputImageRotation.rotation270deg:
        return y * canvasSize.height / imageSize.width;
      case InputImageRotation.rotation0deg:
      case InputImageRotation.rotation180deg:
        return y * canvasSize.height / imageSize.height;
    }
  }

  ({Offset center, double faceWidth, double faceHeight}) mapFaceRect({
    required double left,
    required double top,
    required double width,
    required double height,
  }) {
    final tl = mapPoint(left, top);
    final tr = mapPoint(left + width, top);
    final bl = mapPoint(left, top + height);
    final br = mapPoint(left + width, top + height);
    return (
      center: Offset(
        (tl.dx + tr.dx + bl.dx + br.dx) / 4,
        (tl.dy + tr.dy + bl.dy + br.dy) / 4,
      ),
      faceWidth: (tr.dx - tl.dx).abs(),
      faceHeight: (bl.dy - tl.dy).abs(),
    );
  }
}
