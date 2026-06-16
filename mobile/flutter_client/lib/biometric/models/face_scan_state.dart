import 'dart:ui';

import 'biometric_scan_phase.dart';
import 'overlay_geometry.dart';

/// Estado visual del overlay (solo repinta la capara de camara).
class FaceScanState {
  const FaceScanState({
    required this.displayOval,
    this.targetOval,
    this.debugLandmarks = const [],
    this.visualState = OverlayVisualState.searching,
    this.sweepAngle = 0,
    this.lockProgress = 0,
    this.capturePulse = 0,
    this.hasFace = false,
  });

  final AdaptiveOvalGeometry displayOval;
  final AdaptiveOvalGeometry? targetOval;
  final List<Offset> debugLandmarks;
  final OverlayVisualState visualState;
  final double sweepAngle;
  final double lockProgress;
  final double capturePulse;
  final bool hasFace;

  static const initial = FaceScanState(
    displayOval: AdaptiveOvalGeometry(center: Offset.zero, rx: 88, ry: 104),
  );

  bool visuallyEquals(FaceScanState other) {
    if (visualState != other.visualState || hasFace != other.hasFace) {
      return false;
    }
    if ((sweepAngle - other.sweepAngle).abs() > 0.08) return false;
    if ((lockProgress - other.lockProgress).abs() > 0.02) return false;
    if ((capturePulse - other.capturePulse).abs() > 0.02) return false;
    if (!displayOval.nearEquals(other.displayOval)) return false;
    if (debugLandmarks.length != other.debugLandmarks.length) return false;
    return true;
  }

  FaceScanState copyWith({
    AdaptiveOvalGeometry? displayOval,
    AdaptiveOvalGeometry? targetOval,
    bool clearTargetOval = false,
    List<Offset>? debugLandmarks,
    OverlayVisualState? visualState,
    double? sweepAngle,
    double? lockProgress,
    double? capturePulse,
    bool? hasFace,
  }) {
    return FaceScanState(
      displayOval: displayOval ?? this.displayOval,
      targetOval: clearTargetOval ? null : (targetOval ?? this.targetOval),
      debugLandmarks: debugLandmarks ?? this.debugLandmarks,
      visualState: visualState ?? this.visualState,
      sweepAngle: sweepAngle ?? this.sweepAngle,
      lockProgress: lockProgress ?? this.lockProgress,
      capturePulse: capturePulse ?? this.capturePulse,
      hasFace: hasFace ?? this.hasFace,
    );
  }
}

/// Alias de compatibilidad interna.
typedef BiometricOverlayState = FaceScanState;
