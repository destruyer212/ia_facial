import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../widgets/app_screen_shell.dart';

class WorkerDataScreen extends StatelessWidget {
  const WorkerDataScreen({
    super.key,
    required this.worker,
    required this.onContinue,
    required this.onBack,
  });

  final Map<String, dynamic> worker;
  final VoidCallback onContinue;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return AppScreenShell(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: onBack,
        ),
        title: const Text('Tus datos'),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const BrandHeader(
            title: 'Confirma tus datos',
            subtitle: 'Verifica que la informacion de RRHH sea correcta antes del escaneo facial.',
          ),
          const SizedBox(height: 20),
          Expanded(
            child: ListView(
              children: [
                _InfoTile(label: 'Nombre', value: worker['name'] as String? ?? '-'),
                _InfoTile(
                  label: 'Codigo empleado',
                  value: worker['employee_code'] as String? ?? '-',
                ),
                _InfoTile(label: 'DNI', value: worker['dni'] as String? ?? '-'),
                _InfoTile(label: 'Area', value: worker['area_name'] as String? ?? '-'),
                _InfoTile(label: 'Cargo', value: worker['position_name'] as String? ?? '-'),
                _InfoTile(
                  label: 'Turno',
                  value: [
                    worker['shift_code'],
                    worker['shift_name'],
                    worker['schedule_label'],
                  ].whereType<String>().where((item) => item.isNotEmpty).join(' - '),
                ),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: FilledButton.icon(
              onPressed: onContinue,
              icon: const Icon(Icons.face_retouching_natural),
              label: const Text('Iniciar escaneo facial'),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            softWrap: true,
            style: const TextStyle(
              color: AppColors.textPrimary,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
