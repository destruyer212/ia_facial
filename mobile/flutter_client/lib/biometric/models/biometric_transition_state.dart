enum BiometricTransitionKind {
  idle,
  flash,
  stepSuccess,
  allComplete,
}

class BiometricTransitionState {
  const BiometricTransitionState({
    this.kind = BiometricTransitionKind.idle,
    this.stepKey,
    this.epoch = 0,
  });

  final BiometricTransitionKind kind;
  final String? stepKey;
  final int epoch;

  static const idle = BiometricTransitionState();

  BiometricTransitionState next({
    required BiometricTransitionKind kind,
    String? stepKey,
  }) {
    return BiometricTransitionState(
      kind: kind,
      stepKey: stepKey,
      epoch: epoch + 1,
    );
  }
}
