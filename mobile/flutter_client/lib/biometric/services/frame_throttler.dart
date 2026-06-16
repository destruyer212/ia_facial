class FrameThrottler {
  FrameThrottler({this.intervalMs = 180});

  final int intervalMs;
  DateTime? _lastProcessed;
  bool _busy = false;

  bool shouldProcess() {
    if (_busy) return false;
    final now = DateTime.now();
    if (_lastProcessed != null &&
        now.difference(_lastProcessed!).inMilliseconds < intervalMs) {
      return false;
    }
    return true;
  }

  void markStarted() => _busy = true;

  void markFinished() {
    _busy = false;
    _lastProcessed = DateTime.now();
  }
}
