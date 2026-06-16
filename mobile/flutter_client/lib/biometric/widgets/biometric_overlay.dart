import 'package:flutter/material.dart';

import '../config/biometric_config.dart';
import '../controllers/biometric_scan_controller.dart';
import '../painters/adaptive_face_overlay_painter.dart';

class BiometricOverlay extends StatelessWidget {
  const BiometricOverlay({
    super.key,
    required this.controller,
    this.debugMode = BiometricConfig.debugMode,
  });

  final BiometricScanController controller;
  final bool debugMode;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: ValueListenableBuilder(
        valueListenable: controller.overlayState,
        builder: (context, state, _) {
          return CustomPaint(
            size: controller.canvasSize,
            painter: AdaptiveFaceOverlayPainter(
              state: state,
              debugMode: debugMode,
            ),
          );
        },
      ),
    );
  }
}
