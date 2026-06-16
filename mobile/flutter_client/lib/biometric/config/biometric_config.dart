import 'package:flutter/foundation.dart';

/// Ajustes globales del escaneo facial.
class BiometricConfig {
  const BiometricConfig._();

  /// false en produccion: sin puntos faciales en pantalla.
  static const bool debugMode = kDebugMode ? false : false;

  static const int frameIntervalMs = 160;
  static const int stabilityFrames = 2;
  static const int stabilityBadFrameDecay = 1;
  static const double ovalLerpFactor = 0.38;

  static const double minFaceRatio = 0.12;
  static const double maxFaceRatio = 0.58;

  /// Rostro dentro del ovalo guia visible (1.0 = borde del ovalo).
  static const double guideAlignMax = 1.0;
  /// Centrado perfecto: captura en el siguiente frame bueno.
  static const double guideAlignIdeal = 0.42;

  static const double frontPoseMaxDegrees = 20;
  static const double sidePoseMinDegrees = 12;
  static const double maxHeadTiltDegrees = 16;
}
