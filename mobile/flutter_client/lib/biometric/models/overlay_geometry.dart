import 'dart:ui';

/// Geometria del ovalo guia, suavizada frame a frame.
class AdaptiveOvalGeometry {
  const AdaptiveOvalGeometry({
    required this.center,
    required this.rx,
    required this.ry,
    this.progress = 0,
  });

  final Offset center;
  final double rx;
  final double ry;
  final double progress;

  Rect get bounds => Rect.fromCenter(center: center, width: rx * 2, height: ry * 2);

  AdaptiveOvalGeometry copyWith({
    Offset? center,
    double? rx,
    double? ry,
    double? progress,
  }) {
    return AdaptiveOvalGeometry(
      center: center ?? this.center,
      rx: rx ?? this.rx,
      ry: ry ?? this.ry,
      progress: progress ?? this.progress,
    );
  }

  static AdaptiveOvalGeometry lerp(
    AdaptiveOvalGeometry? from,
    AdaptiveOvalGeometry to, {
    double t = 0.22,
  }) {
    if (from == null) return to;
    return AdaptiveOvalGeometry(
      center: Offset.lerp(from.center, to.center, t)!,
      rx: lerpDouble(from.rx, to.rx, t)!,
      ry: lerpDouble(from.ry, to.ry, t)!,
      progress: lerpDouble(from.progress, to.progress, t)!,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AdaptiveOvalGeometry &&
          other.center == center &&
          other.rx == rx &&
          other.ry == ry &&
          other.progress == progress;

  @override
  int get hashCode => Object.hash(center, rx, ry, progress);

  bool nearEquals(AdaptiveOvalGeometry other, {double epsilon = 1.5}) {
    return (center.dx - other.center.dx).abs() < epsilon &&
        (center.dy - other.center.dy).abs() < epsilon &&
        (rx - other.rx).abs() < epsilon &&
        (ry - other.ry).abs() < epsilon;
  }

  static AdaptiveOvalGeometry fromMappedFace({
    required Offset center,
    required double faceWidth,
    required double faceHeight,
    double padX = 0.55,
    double padY = 0.62,
  }) {
    return AdaptiveOvalGeometry(
      center: center,
      rx: faceWidth * padX,
      ry: faceHeight * padY,
    );
  }
}

class GuideOvalLayout {
  GuideOvalLayout({
    required Size size,
    required double topReserved,
    required double bottomReserved,
  }) {
    final availableHeight =
        (size.height - topReserved - bottomReserved).clamp(180.0, size.height);
    final centerY = topReserved + availableHeight * 0.5;
    center = Offset(size.width / 2, centerY);
    final widthBased = size.width * 0.28;
    final heightBased = availableHeight * 0.26;
    rx = widthBased.clamp(76.0, heightBased).toDouble();
    ry = rx * 1.22;
  }

  late final Offset center;
  late final double rx;
  late final double ry;

  AdaptiveOvalGeometry get guide => AdaptiveOvalGeometry(
        center: center,
        rx: rx,
        ry: ry,
      );
}
