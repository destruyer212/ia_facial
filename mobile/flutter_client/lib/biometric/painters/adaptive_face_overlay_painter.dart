import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../config/biometric_config.dart';
import '../models/biometric_scan_phase.dart';
import '../models/face_scan_state.dart';
import '../models/overlay_geometry.dart';

class AdaptiveFaceOverlayPainter extends CustomPainter {
  AdaptiveFaceOverlayPainter({
    required this.state,
    this.debugMode = BiometricConfig.debugMode,
  });

  final FaceScanState state;
  final bool debugMode;

  static const _amber = Color(0xFFF59E0B);
  static const _cyan = Color(0xFF38BDF8);
  static const _cyanBright = Color(0xFF22D3EE);

  AdaptiveOvalGeometry get _oval {
    final pulse = state.capturePulse.clamp(0.0, 1.0);
    final scale = 1.0 - pulse * 0.06;
    return state.displayOval.copyWith(
      rx: state.displayOval.rx * scale,
      ry: state.displayOval.ry * scale,
    );
  }

  Color get _borderColor => switch (state.visualState) {
        OverlayVisualState.ready => _cyanBright,
        OverlayVisualState.adjusting => _cyan,
        OverlayVisualState.warning => _amber,
        OverlayVisualState.searching => _cyan.withValues(alpha: 0.32),
      };

  @override
  void paint(Canvas canvas, Size size) {
    final oval = _oval;
    _drawVignette(canvas, size, oval);
    if (!state.hasFace && state.targetOval != null) {
      _drawTargetGhost(canvas, state.targetOval!);
    } else if (state.hasFace &&
        state.targetOval != null &&
        state.visualState != OverlayVisualState.ready) {
      _drawTargetGhost(canvas, state.targetOval!);
    }
    _drawOvalBorder(canvas, oval);
    if (debugMode && state.debugLandmarks.isNotEmpty) {
      _drawDebugLandmarks(canvas);
    }
  }

  void _drawVignette(Canvas canvas, Size size, AdaptiveOvalGeometry oval) {
    final full = Path()..addRect(Offset.zero & size);
    final hole = Path()..addOval(oval.bounds);
    final mask = Path.combine(PathOperation.difference, full, hole);
    canvas.drawPath(mask, Paint()..color = const Color(0xD9050A12));
  }

  void _drawTargetGhost(Canvas canvas, AdaptiveOvalGeometry target) {
    canvas.drawOval(
      target.bounds,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = _cyan.withValues(alpha: 0.14),
    );
  }

  void _drawOvalBorder(Canvas canvas, AdaptiveOvalGeometry oval) {
    final rect = oval.bounds;
    final progress = state.lockProgress.clamp(0.0, 1.0);
    final isReady = state.visualState == OverlayVisualState.ready;

    canvas.drawOval(
      rect.inflate(8),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 10
        ..color = _borderColor.withValues(alpha: 0.07)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6),
    );

    if (isReady) {
      canvas.drawOval(
        rect,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.8
          ..shader = SweepGradient(
            colors: [
              _cyanBright.withValues(alpha: 0),
              _cyanBright,
              _cyan,
              _cyanBright.withValues(alpha: 0),
            ],
            stops: const [0.0, 0.12, 0.2, 0.32],
            transform: GradientRotation(state.sweepAngle),
          ).createShader(rect.inflate(2)),
      );
      canvas.drawOval(
        rect,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2
          ..color = _cyan.withValues(alpha: 0.5),
      );
    } else {
      final stroke = state.hasFace ? 2.4 : 1.8;
      final solid = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke
        ..strokeCap = StrokeCap.round
        ..color = _borderColor.withValues(alpha: state.hasFace ? 0.88 : 0.45);

      if (state.hasFace) {
        canvas.drawOval(rect, solid);
      } else {
        const segments = 36;
        const gap = 0.55;
        for (var i = 0; i < segments; i++) {
          final start = (i / segments) * math.pi * 2;
          final sweep = (math.pi * 2 / segments) * (1 - gap);
          canvas.drawArc(rect, start, sweep, false, solid);
        }
      }

      if (progress > 0 && !isReady) {
        canvas.drawArc(
          rect,
          -math.pi / 2,
          math.pi * 2 * progress,
          false,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2.2
            ..strokeCap = StrokeCap.round
            ..color = _cyan.withValues(alpha: 0.9),
        );
      }
    }
  }

  void _drawDebugLandmarks(Canvas canvas) {
    final paint = Paint()
      ..color = _cyan.withValues(alpha: 0.45)
      ..style = PaintingStyle.fill;
    for (final point in state.debugLandmarks) {
      canvas.drawCircle(point, 1.6, paint);
    }
  }

  @override
  bool shouldRepaint(covariant AdaptiveFaceOverlayPainter oldDelegate) {
    if (oldDelegate.debugMode != debugMode) return true;
    return !oldDelegate.state.visuallyEquals(state);
  }
}
