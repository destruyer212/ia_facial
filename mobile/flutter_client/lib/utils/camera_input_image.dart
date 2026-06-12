import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';
import 'dart:ui';

final _orientations = {
  DeviceOrientation.portraitUp: 0,
  DeviceOrientation.landscapeLeft: 90,
  DeviceOrientation.portraitDown: 180,
  DeviceOrientation.landscapeRight: 270,
};

InputImage? inputImageFromCameraImage({
  required CameraImage image,
  required CameraDescription camera,
  required DeviceOrientation deviceOrientation,
}) {
  final rotation = rotationFromCamera(camera, deviceOrientation);
  if (rotation == null) return null;

  final format = InputImageFormatValue.fromRawValue(image.format.raw);
  if (format == null) return null;
  if (Platform.isAndroid && format != InputImageFormat.nv21) return null;
  if (Platform.isIOS && format != InputImageFormat.bgra8888) return null;

  if (image.planes.isEmpty) return null;

  final bytes = _concatenatePlanes(image.planes);
  return InputImage.fromBytes(
    bytes: bytes,
    metadata: InputImageMetadata(
      size: Size(image.width.toDouble(), image.height.toDouble()),
      rotation: rotation,
      format: format,
      bytesPerRow: image.planes.first.bytesPerRow,
    ),
  );
}

InputImageRotation? rotationFromCamera(
  CameraDescription camera,
  DeviceOrientation deviceOrientation,
) {
  final sensorOrientation = camera.sensorOrientation;
  if (Platform.isIOS) {
    return InputImageRotationValue.fromRawValue(sensorOrientation);
  }

  final rotationCompensation = _orientations[deviceOrientation];
  if (rotationCompensation == null) return null;

  var compensated = rotationCompensation;
  if (camera.lensDirection == CameraLensDirection.front) {
    compensated = (sensorOrientation + rotationCompensation) % 360;
  } else {
    compensated = (sensorOrientation - rotationCompensation + 360) % 360;
  }
  return InputImageRotationValue.fromRawValue(compensated);
}

Uint8List _concatenatePlanes(List<Plane> planes) {
  final buffer = WriteBuffer();
  for (final plane in planes) {
    buffer.putUint8List(plane.bytes);
  }
  return buffer.done().buffer.asUint8List();
}

Offset translatePoint({
  required double x,
  required double y,
  required Size canvasSize,
  required Size imageSize,
  required InputImageRotation rotation,
  required CameraLensDirection lensDirection,
}) {
  double translatedX = x;
  double translatedY = y;

  switch (rotation) {
    case InputImageRotation.rotation90deg:
      translatedX = y;
      translatedY = imageSize.width - x;
      break;
    case InputImageRotation.rotation270deg:
      translatedX = imageSize.height - y;
      translatedY = x;
      break;
    case InputImageRotation.rotation180deg:
      translatedX = imageSize.width - x;
      translatedY = imageSize.height - y;
      break;
    case InputImageRotation.rotation0deg:
      break;
  }

  final rotatedWidth = rotation == InputImageRotation.rotation90deg ||
          rotation == InputImageRotation.rotation270deg
      ? imageSize.height
      : imageSize.width;
  final rotatedHeight = rotation == InputImageRotation.rotation90deg ||
          rotation == InputImageRotation.rotation270deg
      ? imageSize.width
      : imageSize.height;

  final scaleX = canvasSize.width / rotatedWidth;
  final scaleY = canvasSize.height / rotatedHeight;
  final scale = scaleX > scaleY ? scaleX : scaleY;

  final offsetX = (canvasSize.width - rotatedWidth * scale) / 2;
  final offsetY = (canvasSize.height - rotatedHeight * scale) / 2;

  var canvasX = translatedX * scale + offsetX;
  final canvasY = translatedY * scale + offsetY;

  if (lensDirection == CameraLensDirection.front) {
    canvasX = canvasSize.width - canvasX;
  }

  return Offset(canvasX, canvasY);
}
