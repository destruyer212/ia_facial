import 'package:flutter/material.dart';

import '../api/face_api_client.dart';

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
    } catch (error) {
      setState(() => _error = 'No se pudo validar el token: $error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Registro facial')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              'Ingresa tu token',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            const Text(
              'RRHH te envio un token unico por correo. No necesitas crear cuenta.',
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _baseUrlController,
              decoration: const InputDecoration(
                labelText: 'URL del servidor',
                hintText: 'http://10.0.2.2:8000',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _tokenController,
              decoration: const InputDecoration(
                labelText: 'Token de registro',
                border: OutlineInputBorder(),
              ),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _validate(),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _loading ? null : _validate,
              child: _loading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Validar token'),
            ),
          ],
        ),
      ),
    );
  }
}
