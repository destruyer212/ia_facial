import 'dart:io';
import 'dart:ui';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

import '../controllers/live_face_register_controller.dart' show FaceFrameMetrics;
import '../models/register_scan_step.dart';
import '../theme/app_theme.dart';
import '../utils/camera_input_image.dart';
import '../utils/responsive.dart';

class GuideCircleGeometry {
  GuideCircleGeometry({
    required Size size,
    required double topReserved,
    required double bottomReserved,
  }) {
    final availableHeight = (size.height - topReserved - bottomReserved).clamp(180.0, size.height);
    final centerY = topReserved + availableHeight * 0.5;
    center = Offset(size.width / 2, centerY);
    final widthBased = size.width * 0.36;
    final heightBased = availableHeight * 0.34;
    radius = widthBased.clamp(88.0, heightBased).toDouble();
  }

  late final Offset center;
  late final double radius;
}

class FaceScanOverlay extends StatelessWidget {
  const FaceScanOverlay({
    super.key,
    required this.metrics,
    required this.canvasSize,
    required this.imageSize,
    required this.rotation,
    required this.lensDirection,
    required this.aligned,
    required this.poseOk,
    required this.stepIndex,
    required this.topReserved,
    required this.bottomReserved,
  });

  final FaceFrameMetrics? metrics;
  final Size canvasSize;
  final Size imageSize;
  final InputImageRotation? rotation;
  final CameraLensDirection lensDirection;
  final bool aligned;
  final bool poseOk;
  final int stepIndex;
  final double topReserved;
  final double bottomReserved;

  @override
  Widget build(BuildContext context) {
    final geometry = GuideCircleGeometry(
      size: canvasSize,
      topReserved: topReserved,
      bottomReserved: bottomReserved,
    );

    return CustomPaint(
      size: canvasSize,
      painter: _FaceScanPainter(
        metrics: metrics,
        canvasSize: canvasSize,
        imageSize: imageSize,
        rotation: rotation ?? InputImageRotation.rotation0deg,
        lensDirection: lensDirection,
        aligned: aligned && poseOk,
        geometry: geometry,
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
    required this.geometry,
  });

  final FaceFrameMetrics? metrics;
  final Size canvasSize;
  final Size imageSize;
  final InputImageRotation rotation;
  final CameraLensDirection lensDirection;
  final bool aligned;
  final GuideCircleGeometry geometry;

  @override
  void paint(Canvas canvas, Size size) {
    _drawDimmedMask(canvas, size);
    _drawGuideCircle(canvas);
    if (metrics != null) {
      _drawMesh(canvas, metrics!);
    }
  }

  void _drawDimmedMask(Canvas canvas, Size size) {
    final background = Path()..addRect(Rect.fromLTWH(0, 0, size.width, size.height));
    final hole = Path()
      ..addOval(Rect.fromCircle(center: geometry.center, radius: geometry.radius));
    final mask = Path.combine(PathOperation.difference, background, hole);
    canvas.drawPath(mask, Paint()..color = const Color(0xCC070D18));
  }

  void _drawGuideCircle(Canvas canvas) {
    final ringColor = aligned ? AppColors.success : AppColors.accent;
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = aligned ? 4 : 3
      ..color = ringColor;
    canvas.drawCircle(geometry.center, geometry.radius, paint);

    if (aligned) {
      canvas.drawCircle(
        geometry.center,
        geometry.radius + 6,
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
        oldDelegate.geometry.center != geometry.center ||
        oldDelegate.geometry.radius != geometry.radius ||
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

  static const _shortLabels = {
    'front': 'Frontal',
    'left': 'Izq.',
    'right': 'Der.',
  };

  @override
  Widget build(BuildContext context) {
    final compact = AppResponsive.isCompact(context);

    return Row(
      children: registerScanSteps.map((step) {
        final done = captures.containsKey(step.key);
        final active = registerScanSteps[stepIndex].key == step.key;
        final label = compact ? (_shortLabels[step.key] ?? step.label) : step.label;

        return Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 3),
            padding: EdgeInsets.symmetric(
              vertical: compact ? 8 : 10,
              horizontal: 4,
            ),
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
              label,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: compact ? 11 : 12,
                fontWeight: FontWeight.w700,
                height: 1.15,
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
    final compact = AppResponsive.isCompact(context);

    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(compact ? 14 : 16),
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
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
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
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: compact ? 16 : 18,
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
