import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/app_screen_shell.dart';

class ConfirmationScreen extends StatelessWidget {
  const ConfirmationScreen({
    super.key,
    required this.message,
    required this.worker,
    required this.onFinish,
  });

  final String message;
  final Map<String, dynamic>? worker;
  final VoidCallback onFinish;

  @override
  Widget build(BuildContext context) {
    final name = worker?['name'] as String? ?? 'Trabajador';
    final code = worker?['employee_code'] as String? ?? '';

    return AppScreenShell(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: AppColors.border),
              boxShadow: [
                BoxShadow(
                  color: AppColors.success.withValues(alpha: 0.12),
                  blurRadius: 40,
                  spreadRadius: 4,
                ),
              ],
            ),
            child: Column(
              children: [
                Container(
                  width: 88,
                  height: 88,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.success.withValues(alpha: 0.15),
                    border: Border.all(color: AppColors.success),
                  ),
                  child: const Icon(
                    Icons.check_rounded,
                    color: AppColors.success,
                    size: 48,
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Registro facial completado',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  '$name${code.isNotEmpty ? ' ($code)' : ''}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 17,
                    color: AppColors.accent,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 28),
          FilledButton(
            onPressed: onFinish,
            child: const Text('Finalizar'),
          ),
        ],
      ),
    );
  }
}
