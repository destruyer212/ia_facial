import 'dart:io';

import 'package:flutter/material.dart';

import '../../models/register_scan_step.dart';
import '../../theme/app_theme.dart';
import '../../utils/responsive.dart';

class ScanProgressBar extends StatelessWidget {
  const ScanProgressBar({
    super.key,
    required this.stepIndex,
    required this.captures,
  });

  final int stepIndex;
  final Map<String, File> captures;

  static const _labels = ['Frontal', 'Izquierda', 'Derecha'];

  @override
  Widget build(BuildContext context) {
    final compact = AppResponsive.isCompact(context);

    return Column(
      children: [
        Row(
          children: List.generate(registerScanSteps.length * 2 - 1, (index) {
            if (index.isOdd) {
              final stepDone = index ~/ 2;
              final done = captures.containsKey(registerScanSteps[stepDone].key);
              return Expanded(
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 320),
                  curve: Curves.easeOutCubic,
                  height: done ? 3 : 2,
                  margin: const EdgeInsets.only(bottom: 18),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(2),
                    color: done ? AppColors.success : AppColors.border,
                    boxShadow: done
                        ? [
                            BoxShadow(
                              color: AppColors.success.withValues(alpha: 0.35),
                              blurRadius: 6,
                            ),
                          ]
                        : null,
                  ),
                ),
              );
            }

            final step = index ~/ 2;
            final stepKey = registerScanSteps[step].key;
            final done = captures.containsKey(stepKey);
            final active = stepIndex == step;

            return _StepDot(
              index: step + 1,
              done: done,
              active: active,
              compact: compact,
            );
          }),
        ),
        Row(
          children: List.generate(registerScanSteps.length, (step) {
            final done = captures.containsKey(registerScanSteps[step].key);
            final active = stepIndex == step;
            return Expanded(
              child: AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOut,
                style: TextStyle(
                  fontSize: compact ? 10 : 11,
                  fontWeight: done || active ? FontWeight.w700 : FontWeight.w600,
                  color: done
                      ? AppColors.success
                      : active
                          ? AppColors.textPrimary
                          : AppColors.textMuted,
                ),
                child: Text(
                  _labels[step],
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}

class _StepDot extends StatelessWidget {
  const _StepDot({
    required this.index,
    required this.done,
    required this.active,
    required this.compact,
  });

  final int index;
  final bool done;
  final bool active;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final size = compact ? 26.0 : 30.0;
    final color = done
        ? AppColors.success
        : active
            ? AppColors.accent
            : AppColors.surfaceLight;

    return SizedBox(
      width: size + 8,
      child: Column(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: done
                  ? AppColors.success.withValues(alpha: 0.2)
                  : active
                      ? AppColors.accent.withValues(alpha: 0.15)
                      : AppColors.surfaceLight,
              border: Border.all(
                color: color,
                width: active || done ? 2 : 1,
              ),
              boxShadow: active
                  ? [
                      BoxShadow(
                        color: AppColors.accent.withValues(alpha: 0.35),
                        blurRadius: 12,
                      ),
                    ]
                  : null,
            ),
            child: Center(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 260),
                switchInCurve: Curves.elasticOut,
                switchOutCurve: Curves.easeIn,
                transitionBuilder: (child, animation) {
                  return ScaleTransition(scale: animation, child: child);
                },
                child: done
                    ? Icon(
                        Icons.check_rounded,
                        key: ValueKey('check-$index'),
                        size: 15,
                        color: AppColors.success,
                      )
                    : Text(
                        '$index',
                        key: ValueKey('num-$index'),
                        style: TextStyle(
                          fontSize: compact ? 11 : 12,
                          fontWeight: FontWeight.w700,
                          color:
                              active ? AppColors.accent : AppColors.textMuted,
                        ),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
