import 'package:flutter/material.dart';

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

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.check_circle, color: Colors.green, size: 88),
              const SizedBox(height: 20),
              const Text(
                'Registro facial completado',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              Text(
                '$name${code.isNotEmpty ? ' ($code)' : ''}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 18),
              ),
              const SizedBox(height: 12),
              Text(
                message,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              FilledButton(
                onPressed: onFinish,
                child: const Text('Finalizar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
