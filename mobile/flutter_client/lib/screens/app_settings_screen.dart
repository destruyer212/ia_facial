import 'package:flutter/material.dart';

import '../api/face_api_client.dart';
import '../config/api_config.dart';
import '../config/api_preferences.dart';
import '../theme/app_theme.dart';
import '../widgets/app_screen_shell.dart';

class AppSettingsScreen extends StatefulWidget {
  const AppSettingsScreen({
    super.key,
    required this.initialBaseUrl,
  });

  final String initialBaseUrl;

  @override
  State<AppSettingsScreen> createState() => _AppSettingsScreenState();
}

class _AppSettingsScreenState extends State<AppSettingsScreen> {
  final _controller = TextEditingController();
  bool _loading = false;
  String? _error;
  String? _success;

  @override
  void initState() {
    super.initState();
    _controller.text = widget.initialBaseUrl;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final url = _controller.text.trim().replaceAll(RegExp(r'/+$'), '');
    if (url.isEmpty) {
      setState(() {
        _error = 'Ingresa la URL del servidor API.';
        _success = null;
      });
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _success = null;
    });

    try {
      final client = FaceApiClient(baseUrl: url);
      await client.wakeUpServer();
      await ApiPreferences.save(url);
      if (!mounted) return;
      setState(() {
        _success = 'Conexion guardada y verificada.';
      });
      await Future<void>.delayed(const Duration(milliseconds: 500));
      if (mounted) Navigator.of(context).pop(url);
    } on FaceApiException catch (error) {
      setState(() => _error = error.detail);
    } catch (error) {
      setState(() => _error = 'No se pudo conectar: $error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScreenShell(
      scrollable: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: _loading ? null : () => Navigator.of(context).pop(),
                icon: const Icon(Icons.arrow_back, color: Colors.white),
              ),
              const Expanded(
                child: Text(
                  'Configuracion',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                  ),
                ),
              ),
              const SizedBox(width: 48),
            ],
          ),
          const SizedBox(height: 12),
          const BrandHeader(
            title: 'Servidor API',
            subtitle:
                'Define la URL del backend que usa esta app movil. El cambio aplica a todo el registro facial.',
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _controller,
                  enabled: !_loading,
                  keyboardType: TextInputType.url,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'URL del API',
                    hintText: kProductionApiBaseUrl,
                    prefixIcon: Icon(Icons.cloud_outlined, color: AppColors.accent),
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Ej: $kProductionApiBaseUrl en produccion.',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 12, height: 1.4),
                ),
              ],
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 14),
            _messageBox(_error!, isError: true),
          ],
          if (_success != null) ...[
            const SizedBox(height: 14),
            _messageBox(_success!, isError: false),
          ],
          const SizedBox(height: 28),
          FilledButton(
            onPressed: _loading ? null : _save,
            child: _loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Text('Guardar y probar conexion'),
          ),
        ],
      ),
    );
  }

  Widget _messageBox(String text, {required bool isError}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: (isError ? Colors.red : AppColors.accent).withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: (isError ? Colors.red : AppColors.accent).withValues(alpha: 0.35),
        ),
      ),
      child: Text(
        text,
        style: TextStyle(color: isError ? const Color(0xFFFCA5A5) : AppColors.accent),
      ),
    );
  }
}
