import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

class QualityWarningChip extends StatelessWidget {
  const QualityWarningChip({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 200),
      child: Container(
        key: ValueKey(message),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF1A2740).withValues(alpha: 0.92),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: const Color(0xFFF59E0B).withValues(alpha: 0.55),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _iconFor(message),
              size: 16,
              color: const Color(0xFFF59E0B),
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                message,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _iconFor(String message) {
    final lower = message.toLowerCase();
    if (lower.contains('iluminacion') || lower.contains('luz')) {
      return Icons.wb_sunny_outlined;
    }
    if (lower.contains('quieto')) return Icons.accessibility_new;
    if (lower.contains('acerca') || lower.contains('aleja')) {
      return Icons.straighten;
    }
    if (lower.contains('ojos')) return Icons.visibility_outlined;
    return Icons.info_outline;
  }
}
