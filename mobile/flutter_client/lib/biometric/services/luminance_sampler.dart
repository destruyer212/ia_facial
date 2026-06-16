import 'dart:io';
import 'dart:ui';

import 'package:camera/camera.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

/// Muestrea luminancia media (Y) en el ROI facial del buffer NV21/BGRA.
class LuminanceSampler {
  static double? sampleFaceRegion({
    required CameraImage image,
    required Face face,
  }) {
    if (Platform.isAndroid) {
      return _sampleNv21(image, face.boundingBox);
    }
    if (Platform.isIOS) {
      return _sampleBgra(image, face.boundingBox);
    }
    return null;
  }

  static double? _sampleNv21(CameraImage image, Rect box) {
    if (image.planes.isEmpty) return null;
    final yPlane = image.planes.first.bytes;
    final width = image.width;
    final height = image.height;

    final left = box.left.clamp(0, width - 1).toInt();
    final top = box.top.clamp(0, height - 1).toInt();
    final right = box.right.clamp(left + 1, width).toInt();
    final bottom = box.bottom.clamp(top + 1, height).toInt();

    var sum = 0;
    var count = 0;
    final stepX = ((right - left) / 8).ceil().clamp(1, 999);
    final stepY = ((bottom - top) / 8).ceil().clamp(1, 999);

    for (var y = top; y < bottom; y += stepY) {
      for (var x = left; x < right; x += stepX) {
        final index = y * width + x;
        if (index >= 0 && index < yPlane.length) {
          sum += yPlane[index];
          count++;
        }
      }
    }
    if (count == 0) return null;
    return sum / count;
  }

  static double? _sampleBgra(CameraImage image, Rect box) {
    if (image.planes.isEmpty) return null;
    final bytes = image.planes.first.bytes;
    final bytesPerRow = image.planes.first.bytesPerRow;
    final width = image.width;
    final height = image.height;

    final left = box.left.clamp(0, width - 1).toInt();
    final top = box.top.clamp(0, height - 1).toInt();
    final right = box.right.clamp(left + 1, width).toInt();
    final bottom = box.bottom.clamp(top + 1, height).toInt();

    var sum = 0;
    var count = 0;
    final stepX = ((right - left) / 6).ceil().clamp(1, 999);
    final stepY = ((bottom - top) / 6).ceil().clamp(1, 999);

    for (var y = top; y < bottom; y += stepY) {
      for (var x = left; x < right; x += stepX) {
        final offset = y * bytesPerRow + x * 4;
        if (offset + 2 < bytes.length) {
          final b = bytes[offset];
          final g = bytes[offset + 1];
          final r = bytes[offset + 2];
          sum += (0.299 * r + 0.587 * g + 0.114 * b).round();
          count++;
        }
      }
    }
    if (count == 0) return null;
    return sum / count;
  }
}
