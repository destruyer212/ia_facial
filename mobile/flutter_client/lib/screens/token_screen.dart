import 'dart:io';

import 'package:flutter/material.dart';

import '../api/face_api_client.dart';
import '../config/api_config.dart';
import '../theme/app_theme.dart';
import '../widgets/app_screen_shell.dart';

class TokenScreen extends StatefulWidget {
  const TokenScreen({
    super.key,
    required this.baseUrl,
    required this.onBaseUrlChanged,
    required this.onValidated,
  });

  final String baseUrl;
  final ValueChanged<String> onBaseUrlChanged;
  final void Function(String token, Map<String, dynamic> worker) onValidated;

  @override
  State<TokenScreen> createState() => _TokenScreenState();
}

class _TokenScreenState extends State<TokenScreen> {
  final _tokenController = TextEditingController();
  final _baseUrlController = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _baseUrlController.text = widget.baseUrl;
  }

  @override
  void dispose() {
    _tokenController.dispose();
    _baseUrlController.dispose();
    super.dispose();
  }

  Future<void> _validate() async {
    final token = _tokenController.text.trim();
    if (token.length < 8) {
      setState(() => _error = 'Ingresa el token enviado por correo.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      widget.onBaseUrlChanged(_baseUrlController.text);
      final client = FaceApiClient(baseUrl: _baseUrlController.text.trim());
      final response = await client.validateRegistrationToken(token);
      final valid = response['valid'] == true;
      if (!valid) {
        setState(() {
          _error = response['message'] as String? ?? 'Token invalido.';
          _loading = false;
        });
        return;
      }
      final worker = response['worker'] as Map<String, dynamic>?;
      if (worker == null) {
        setState(() {
          _error = 'No se recibieron datos del trabajador.';
          _loading = false;
        });
        return;
      }
      widget.onValidated(token, worker);
    } on FaceApiException catch (error) {
      setState(() => _error = error.body);
    } on SocketException {
      setState(() => _error =
          'Sin conexion al servidor. Verifica tu internet y la URL $kProductionApiBaseUrl');
    } catch (error) {
      final message = error.toString();
      if (message.contains('Connection timed out') ||
          message.contains('10.0.2.2')) {
        setState(() => _error =
            'No llega al servidor. Usa: $kProductionApiBaseUrl');
        return;
      }
      setState(() => _error = 'No se pudo validar el token: $error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScreenShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const BrandHeader(
            title: 'Ingresa tu token',
            subtitle:
                'RRHH te envio un token unico por correo. No necesitas crear cuenta.',
          ),
          const SizedBox(height: 28),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                TextField(
                  controller: _baseUrlController,
                  style: const TextStyle(color: AppColors.textPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Servidor',
                    prefixIcon: Icon(Icons.cloud_outlined, color: AppColors.accent),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _tokenController,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    letterSpacing: 1.2,
                    fontWeight: FontWeight.w600,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Token de registro',
                    prefixIcon: Icon(Icons.vpn_key_outlined, color: AppColors.accent),
                  ),
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => _validate(),
                ),
              ],
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.red.withValues(alpha: 0.35)),
              ),
              child: Text(
                _error!,
                style: const TextStyle(color: Color(0xFFFCA5A5)),
              ),
            ),
          ],
          const Spacer(),
          FilledButton(
            onPressed: _loading ? null : _validate,
            child: _loading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('Validar token'),
          ),
        ],
      ),
    );
  }
}
