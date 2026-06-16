import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../theme/app_theme.dart';
import '../controllers/biometric_scan_controller.dart';
import '../models/biometric_transition_state.dart';

/// Flash de captura + badge de exito sobre el ovalo guia.
class CaptureTransitionLayer extends StatefulWidget {
  const CaptureTransitionLayer({
    super.key,
    required this.controller,
  });

  final BiometricScanController controller;

  @override
  State<CaptureTransitionLayer> createState() => _CaptureTransitionLayerState();
}

class _CaptureTransitionLayerState extends State<CaptureTransitionLayer>
    with TickerProviderStateMixin {
  late final AnimationController _flashController;
  late final AnimationController _successController;
  late final Animation<double> _flashOpacity;
  late final Animation<double> _successScale;
  late final Animation<double> _successOpacity;

  BiometricTransitionKind _kind = BiometricTransitionKind.idle;
  int _lastEpoch = -1;

  @override
  void initState() {
    super.initState();
    _flashController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    );
    _successController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 520),
    );

    _flashOpacity = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 0.0, end: 0.62).chain(
          CurveTween(curve: Curves.easeOut),
        ),
        weight: 35,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 0.62, end: 0.0).chain(
          CurveTween(curve: Curves.easeIn),
        ),
        weight: 65,
      ),
    ]).animate(_flashController);

    _successScale = Tween<double>(begin: 0.55, end: 1.0).animate(
      CurvedAnimation(
        parent: _successController,
        curve: Curves.elasticOut,
      ),
    );
    _successOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _successController,
        curve: const Interval(0.0, 0.35, curve: Curves.easeOut),
      ),
    );

    widget.controller.transitionState.addListener(_onTransition);
  }

  void _onTransition() {
    final next = widget.controller.transitionState.value;
    if (next.epoch == _lastEpoch) return;
    _lastEpoch = next.epoch;

    setState(() => _kind = next.kind);

    switch (next.kind) {
      case BiometricTransitionKind.flash:
        _successController.reset();
        _flashController.forward(from: 0);
      case BiometricTransitionKind.stepSuccess:
      case BiometricTransitionKind.allComplete:
        _successController.forward(from: 0);
      case BiometricTransitionKind.idle:
        break;
    }
  }

  @override
  void dispose() {
    widget.controller.transitionState.removeListener(_onTransition);
    _flashController.dispose();
    _successController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final guide = widget.controller.overlayState.value.displayOval;
    final center = guide.center;
    final isAllDone = _kind == BiometricTransitionKind.allComplete;

    return IgnorePointer(
      child: Stack(
        fit: StackFit.expand,
        children: [
          AnimatedBuilder(
            animation: _flashController,
            builder: (context, _) {
              if (_flashController.value == 0) return const SizedBox.shrink();
              return ColoredBox(
                color: Colors.white.withValues(alpha: _flashOpacity.value),
              );
            },
          ),
          if (_kind == BiometricTransitionKind.stepSuccess ||
              _kind == BiometricTransitionKind.allComplete)
            AnimatedBuilder(
              animation: _successController,
              builder: (context, _) {
                if (_successController.value == 0) return const SizedBox.shrink();

                final size = isAllDone ? 88.0 : 72.0;
                return Positioned(
                  left: center.dx - size / 2,
                  top: center.dy - size / 2,
                  child: Opacity(
                    opacity: _successOpacity.value,
                    child: Transform.scale(
                      scale: _successScale.value,
                      child: Container(
                        width: size,
                        height: size,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.success.withValues(alpha: 0.92),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.success.withValues(alpha: 0.45),
                              blurRadius: 28,
                              spreadRadius: 2,
                            ),
                          ],
                        ),
                        child: Icon(
                          isAllDone ? Icons.verified_rounded : Icons.check_rounded,
                          color: Colors.white,
                          size: isAllDone ? 42 : 36,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          if (_kind == BiometricTransitionKind.allComplete &&
              _successController.value > 0.4)
            Positioned(
              left: 24,
              right: 24,
              top: guide.center.dy + 56,
              child: FadeTransition(
                opacity: CurvedAnimation(
                  parent: _successController,
                  curve: const Interval(0.35, 1.0, curve: Curves.easeOut),
                ),
                child: const Text(
                  'Escaneo completo',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    shadows: [
                      Shadow(
                        color: Color(0xAA000000),
                        blurRadius: 12,
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Retroalimentacion tactil en capturas exitosas.
void biometricCaptureHaptic(BiometricTransitionKind kind) {
  switch (kind) {
    case BiometricTransitionKind.flash:
      HapticFeedback.mediumImpact();
    case BiometricTransitionKind.stepSuccess:
      HapticFeedback.lightImpact();
    case BiometricTransitionKind.allComplete:
      HapticFeedback.heavyImpact();
    case BiometricTransitionKind.idle:
      break;
  }
}
