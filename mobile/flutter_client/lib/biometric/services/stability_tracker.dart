import '../config/biometric_config.dart';

class StabilityTracker {
  StabilityTracker({
    int? requiredGoodFrames,
    int? badFrameDecay,
  })  : requiredGoodFrames =
            requiredGoodFrames ?? BiometricConfig.stabilityFrames,
        badFrameDecay = badFrameDecay ?? BiometricConfig.stabilityBadFrameDecay;

  final int requiredGoodFrames;
  final int badFrameDecay;
  int _good = 0;

  void reset() => _good = 0;

  bool register(bool isGood, {bool aligned = false}) {
    if (isGood) {
      if (aligned) {
        _good = requiredGoodFrames;
      } else {
        _good++;
      }
    } else if (_good > 0) {
      _good = (_good - badFrameDecay).clamp(0, requiredGoodFrames);
    }
    return _good >= requiredGoodFrames;
  }

  double get progress => (_good / requiredGoodFrames).clamp(0.0, 1.0);
}
