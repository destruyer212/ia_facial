import '../config/biometric_config.dart';

class StabilityTracker {
  StabilityTracker({
    int? requiredGoodFrames,
    int? badFrameDecay,
  })  : requiredGoodFrames =
            requiredGoodFrames ?? BiometricConfig.stabilityFramesFront,
        badFrameDecay = badFrameDecay ?? BiometricConfig.stabilityBadFrameDecay;

  int requiredGoodFrames;
  int badFrameDecay;
  int _good = 0;

  void reset() => _good = 0;

  bool register(bool isGood) {
    if (isGood) {
      _good++;
    } else if (_good > 0) {
      _good = (_good - badFrameDecay).clamp(0, requiredGoodFrames);
    }
    return _good >= requiredGoodFrames;
  }

  double get progress => (_good / requiredGoodFrames).clamp(0.0, 1.0);
}
