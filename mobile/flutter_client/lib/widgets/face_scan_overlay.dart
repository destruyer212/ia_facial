import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

import '../controllers/live_face_register_controller.dart';
import '../models/register_scan_step.dart';
import '../theme/app_theme.dart';
import '../utils/camera_input_image.dart';

class FaceScanOverlay extends StatelessWidget {
  const FaceScanOverlay({
    super.key,
    required this.controller,
    required this.metrics,
    required this.canvasSize,
    required this.imageSize,
    required this.rotation,
    required this.lensDirection,
    required this.aligned,
    required this.poseOk,
    required this.stepIndex,
  });

  final LiveFaceRegisterController controller;
  final FaceFrameMetrics? metrics;
  final Size canvasSize;
  final Size imageSize;
  final InputImageRotation? rotation;
  final CameraLensDirection lensDirection;
  final bool aligned;
  final bool poseOk;
  final int stepIndex;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: canvasSize,
      painter: _FaceScanPainter(
        metrics: metrics,
        canvasSize: canvasSize,
        imageSize: imageSize,
        rotation: rotation ?? InputImageRotation.rotation0deg,
        lensDirection: lensDirection,
        aligned: aligned && poseOk,
        stepIndex: stepIndex,
      ),
    );
  }
}

class _FaceScanPainter extends CustomPainter {
  _FaceScanPainter({
    required this.metrics,
    required this.canvasSize,
    required this.imageSize,
    required this.rotation,
    required this.lensDirection,
    required this.aligned,
    required this.stepIndex,
  });

  final FaceFrameMetrics? metrics;
  final Size canvasSize;
  final Size imageSize;
  final InputImageRotation rotation;
  final CameraLensDirection lensDirection;
  final bool aligned;
  final int stepIndex;

  @override
  void paint(Canvas canvas, Size size) {
    _drawDimmedMask(canvas, size);
    _drawGuideCircle(canvas, size);
    if (metrics != null) {
      _drawMesh(canvas, metrics!);
    }
  }

  void _drawDimmedMask(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * 0.42);
    final radius = size.width * 0.36;
    final background = Path()..addRect(Rect.fromLTWH(0, 0, size.width, size.height));
    final hole = Path()
      ..addOval(Rect.fromCircle(center: center, radius: radius));
    final mask = Path.combine(PathOperation.difference, background, hole);
    canvas.drawPath(mask, Paint()..color = const Color(0xCC070D18));
  }

  void _drawGuideCircle(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * 0.42);
    final radius = size.width * 0.36;
    final ringColor = aligned ? AppColors.success : AppColors.accent;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = aligned ? 4 : 3
      ..color = ringColor;
    canvas.drawCircle(center, radius, paint);

    if (aligned) {
      canvas.drawCircle(
        center,
        radius + 6,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..color = AppColors.accentGlow,
      );
    }
  }

  void _drawMesh(Canvas canvas, FaceFrameMetrics metrics) {
    if (imageSize == Size.zero) return;
    for (final point in metrics.meshPoints) {
      final translated = translatePoint(
        x: point.dx,
        y: point.dy,
        canvasSize: canvasSize,
        imageSize: imageSize,
        rotation: rotation,
        lensDirection: lensDirection,
      );
      canvas.drawCircle(
        translated,
        3.2,
        Paint()..color = AppColors.accentGlow,
      );
      canvas.drawCircle(
        translated,
        1.6,
        Paint()..color = AppColors.accent,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _FaceScanPainter oldDelegate) {
    return oldDelegate.metrics != metrics ||
        oldDelegate.aligned != aligned ||
        oldDelegate.stepIndex != stepIndex ||
        oldDelegate.canvasSize != canvasSize;
  }
}

class ScanStepChips extends StatelessWidget {
  const ScanStepChips({
    super.key,
    required this.stepIndex,
    required this.captures,
  });

  final int stepIndex;
  final Map<String, File> captures;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: registerScanSteps.map((step) {
        final done = captures.containsKey(step.key);
        final active = registerScanSteps[stepIndex].key == step.key;
        return Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: done
                  ? AppColors.success.withValues(alpha: 0.18)
                  : active
                      ? AppColors.accent.withValues(alpha: 0.18)
                      : AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: done
                    ? AppColors.success
                    : active
                        ? AppColors.accent
                        : AppColors.border,
              ),
            ),
            child: Text(
              step.label,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: done || active ? AppColors.textPrimary : AppColors.textMuted,
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

class ScanStatusCard extends StatelessWidget {
  const ScanStatusCard({
    super.key,
    required this.title,
    required this.hint,
    required this.stepLabel,
  });

  final String title;
  final String hint;
  final String stepLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x66000000),
            blurRadius: 24,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            stepLabel,
            style: const TextStyle(
              color: AppColors.accent,
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.4,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            title,
            style: const TextStyle(
              color: AppColors.textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            hint,
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 14,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }
}
