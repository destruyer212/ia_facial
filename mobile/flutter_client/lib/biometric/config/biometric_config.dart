import 'package:flutter/foundation.dart';

/// Ajustes globales del escaneo facial.
class BiometricConfig {
  const BiometricConfig._();

  /// false en produccion: sin puntos faciales en pantalla.
  static const bool debugMode = kDebugMode ? false : false;

  static const int frameIntervalMs = 150;
  static const int stabilityFramesFront = 8;
  static const int stabilityFramesSide = 5;
  static const int stabilityBadFrameDecay = 2;
  static const double ovalLerpFactor = 0.38;

  static const double minFaceRatio = 0.10;
  static const double maxFaceRatio = 0.62;

  /// Rostro dentro del ovalo guia visible (1.0 = borde del ovalo).
  static const double guideAlignMax = 0.88;
  /// Centrado estricto antes de avanzar el contador de estabilidad.
  static const double guideAlignIdeal = 0.30;

  static const double frontPoseMaxDegrees = 14;
  static const double sidePoseMinDegrees = 16;
  static const double maxHeadTiltDegrees = 14;

  static int stabilityFramesFor(String stepKey) =>
      stepKey == 'front' ? stabilityFramesFront : stabilityFramesSide;
}
