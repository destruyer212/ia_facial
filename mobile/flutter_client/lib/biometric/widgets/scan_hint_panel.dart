import 'dart:ui';

import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../utils/responsive.dart';

class ScanHintPanel extends StatelessWidget {
  const ScanHintPanel({
    super.key,
    required this.stepLabel,
    required this.title,
    required this.hint,
    this.stabilityProgress = 0,
    this.transitionKey,
  });

  final String stepLabel;
  final String title;
  final String hint;
  final double stabilityProgress;
  final Object? transitionKey;

  @override
  Widget build(BuildContext context) {
    final compact = AppResponsive.isCompact(context);
    final contentKey = transitionKey ?? '$stepLabel|$title';

    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
        child: Container(
          width: double.infinity,
          padding: EdgeInsets.all(compact ? 16 : 18),
          decoration: BoxDecoration(
            color: AppColors.surface.withValues(alpha: 0.72),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: AppColors.border.withValues(alpha: 0.65),
            ),
            boxShadow: const [
              BoxShadow(
                color: Color(0x55000000),
                blurRadius: 28,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 220),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  return FadeTransition(
                    opacity: animation,
                    child: SlideTransition(
                      position: Tween<Offset>(
                        begin: const Offset(0, 0.12),
                        end: Offset.zero,
                      ).animate(animation),
                      child: child,
                    ),
                  );
                },
                child: Text(
                  stepLabel,
                  key: ValueKey('step-$contentKey'),
                  style: const TextStyle(
                    color: AppColors.accent,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 240),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  return FadeTransition(
                    opacity: animation,
                    child: SlideTransition(
                      position: Tween<Offset>(
                        begin: const Offset(0, 0.18),
                        end: Offset.zero,
                      ).animate(animation),
                      child: child,
                    ),
                  );
                },
                child: Text(
                  title,
                  key: ValueKey('title-$contentKey'),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: compact ? 20 : 22,
                    fontWeight: FontWeight.w800,
                    height: 1.15,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                child: Text(
                  hint,
                  key: ValueKey('hint-$hint'),
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 14,
                    height: 1.4,
                  ),
                ),
              ),
          if (stabilityProgress > 0.04 && stabilityProgress < 0.98) ...[
            const SizedBox(height: 14),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0, end: stabilityProgress),
                duration: const Duration(milliseconds: 280),
                curve: Curves.easeOutCubic,
                builder: (context, value, _) {
                  return LinearProgressIndicator(
                    value: value,
                    minHeight: 4,
                    color: const Color(0xFF22D3EE),
                    backgroundColor: AppColors.surfaceLight,
                  );
                },
              ),
            ),
          ],
            ],
          ),
        ),
      ),
    );
  }
}
