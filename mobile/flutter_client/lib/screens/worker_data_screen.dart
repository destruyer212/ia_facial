import 'package:flutter/material.dart';

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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tus datos'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: onBack,
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Confirma que estos datos son correctos',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 20),
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
              const Spacer(),
              FilledButton(
                onPressed: onContinue,
                child: const Text('Continuar al registro facial'),
              ),
            ],
          ),
        ),
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
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        title: Text(label),
        subtitle: Text(
          value,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
