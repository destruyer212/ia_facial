import 'dart:io';

import 'package:flutter/material.dart';

import '../api/face_api_client.dart';
import '../config/api_config.dart';
import '../theme/app_theme.dart';
import '../widgets/app_screen_shell.dart';
import 'app_settings_screen.dart';

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
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _openSettings() async {
    final newUrl = await Navigator.of(context).push<String>(
      MaterialPageRoute(
        builder: (_) => AppSettingsScreen(initialBaseUrl: widget.baseUrl),
      ),
    );
    if (newUrl != null && newUrl.isNotEmpty) {
      widget.onBaseUrlChanged(newUrl);
    }
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
      final client = FaceApiClient(baseUrl: widget.baseUrl.trim());
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
          'Sin conexion al servidor. Ve a Configuracion y revisa la URL ($kProductionApiBaseUrl).');
    } catch (error) {
      final message = error.toString();
      if (message.contains('Connection timed out') ||
          message.contains('10.0.2.2')) {
        setState(() => _error =
            'No llega al servidor. Ve a Configuracion y usa: $kProductionApiBaseUrl');
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
      scrollable: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: _loading ? null : _openSettings,
              icon: const Icon(Icons.settings_outlined, size: 18),
              label: const Text('Configuracion'),
            ),
          ),
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
            child: TextField(
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
