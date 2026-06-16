import 'dart:io';

import 'biometric_scan_phase.dart';
import 'face_quality_issue.dart';

class BiometricUiState {
  const BiometricUiState({
    this.phase = BiometricScanPhase.idle,
    this.statusTitle = 'Preparando',
    this.statusHint = 'Iniciando camara...',
    this.warningHint,
    this.stepIndex = 0,
    this.stabilityProgress = 0,
    this.captures = const {},
    this.errorMessage,
  });

  final BiometricScanPhase phase;
  final String statusTitle;
  final String statusHint;
  final String? warningHint;
  final int stepIndex;
  final double stabilityProgress;
  final Map<String, File> captures;
  final String? errorMessage;

  BiometricUiState copyWith({
    BiometricScanPhase? phase,
    String? statusTitle,
    String? statusHint,
    String? warningHint,
    bool clearWarning = false,
    int? stepIndex,
    double? stabilityProgress,
    Map<String, File>? captures,
    String? errorMessage,
    bool clearError = false,
  }) {
    return BiometricUiState(
      phase: phase ?? this.phase,
      statusTitle: statusTitle ?? this.statusTitle,
      statusHint: statusHint ?? this.statusHint,
      warningHint: clearWarning ? null : (warningHint ?? this.warningHint),
      stepIndex: stepIndex ?? this.stepIndex,
      stabilityProgress: stabilityProgress ?? this.stabilityProgress,
      captures: captures ?? this.captures,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

extension FaceQualityIssueX on FaceQualityIssue {
  bool get isWarning =>
      this != FaceQualityIssue.none && this != FaceQualityIssue.noFace;
}
