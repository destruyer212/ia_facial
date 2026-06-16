import 'dart:ui';

import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

import '../../models/register_scan_step.dart';
import '../config/biometric_config.dart';
import '../models/face_quality_issue.dart';
import '../models/overlay_geometry.dart';

class FaceQualityAnalyzer {
  const FaceQualityAnalyzer({
    this.minFaceRatio = BiometricConfig.minFaceRatio,
    this.maxFaceRatio = BiometricConfig.maxFaceRatio,
  });

  final double minFaceRatio;
  final double maxFaceRatio;

  /// Distancia normalizada al centro del ovalo guia (0 = centro perfecto).
  static double guideAlignmentScore({
    required Offset mappedCenter,
    required AdaptiveOvalGeometry guide,
  }) {
    final dx = (mappedCenter.dx - guide.center.dx) / (guide.rx * 0.92);
    final dy = (mappedCenter.dy - guide.center.dy) / (guide.ry * 0.92);
    return dx * dx + dy * dy;
  }

  FaceQualityIssue analyze({
    required List<Face> faces,
    required double imageWidth,
    required RegisterScanStep step,
    required Offset mappedCenter,
    required AdaptiveOvalGeometry guide,
  }) {
    if (faces.isEmpty) return FaceQualityIssue.noFace;
    if (faces.length > 1) return FaceQualityIssue.multipleFaces;

    final face = faces.first;
    final ratio = face.boundingBox.width / imageWidth;

    if (ratio < minFaceRatio) return FaceQualityIssue.tooFar;
    if (ratio > maxFaceRatio) return FaceQualityIssue.tooClose;

    final alignScore = guideAlignmentScore(
      mappedCenter: mappedCenter,
      guide: guide,
    );
    if (alignScore > BiometricConfig.guideAlignMax) {
      return FaceQualityIssue.offCenter;
    }

    final y = face.headEulerAngleY ?? 0;
    final z = face.headEulerAngleZ ?? 0;

    if (z.abs() > BiometricConfig.maxHeadTiltDegrees) {
      return FaceQualityIssue.badPose;
    }

    if (step.key == 'front') {
      if (y.abs() > BiometricConfig.frontPoseMaxDegrees) {
        return FaceQualityIssue.badPose;
      }
    } else if (!step.matchesPose(y)) {
      return FaceQualityIssue.badPose;
    }

    return FaceQualityIssue.none;
  }

  bool isIdealAlignment(double alignScore) =>
      alignScore <= BiometricConfig.guideAlignIdeal;

  String hintFor(FaceQualityIssue issue, RegisterScanStep step) {
    return switch (issue) {
      FaceQualityIssue.noFace => 'Centra tu rostro en el ovalo',
      FaceQualityIssue.multipleFaces => 'Solo una persona',
      FaceQualityIssue.tooFar => 'Acercate un poco',
      FaceQualityIssue.tooClose => 'Alejate un poco',
      FaceQualityIssue.offCenter => 'Centra tu rostro en el ovalo',
      FaceQualityIssue.badPose => step.prompt,
      FaceQualityIssue.eyesClosed => 'Abre los ojos',
      FaceQualityIssue.lowLight => 'Mejora la luz',
      FaceQualityIssue.tooBright => 'Menos luz directa',
      FaceQualityIssue.unstable => 'Mantente quieto',
      FaceQualityIssue.none => step.prompt,
    };
  }

  bool isSecondaryWarning(FaceQualityIssue issue) {
    return switch (issue) {
      FaceQualityIssue.tooFar ||
      FaceQualityIssue.tooClose =>
        true,
      _ => false,
    };
  }
}
