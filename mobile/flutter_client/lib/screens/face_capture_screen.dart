import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api/face_api_client.dart';

class FaceCaptureScreen extends StatefulWidget {
  const FaceCaptureScreen({
    super.key,
    required this.apiClient,
    required this.token,
    required this.worker,
    required this.onCompleted,
    required this.onBack,
  });

  final FaceApiClient apiClient;
  final String token;
  final Map<String, dynamic> worker;
  final ValueChanged<Map<String, dynamic>> onCompleted;
  final VoidCallback onBack;

  @override
  State<FaceCaptureScreen> createState() => _FaceCaptureScreenState();
}

class _FaceCaptureScreenState extends State<FaceCaptureScreen> {
  final _picker = ImagePicker();
  final _steps = const [
    _CaptureStep(key: 'front', title: 'Foto frontal', hint: 'Mira directo a la camara'),
    _CaptureStep(key: 'left', title: 'Giro izquierda', hint: 'Gira levemente hacia tu izquierda'),
    _CaptureStep(key: 'right', title: 'Giro derecha', hint: 'Gira levemente hacia tu derecha'),
  ];

  final Map<String, File?> _captures = {
    'front': null,
    'left': null,
    'right': null,
  };

  int _currentStep = 0;
  bool _submitting = false;
  String? _error;

  Future<void> _captureCurrent() async {
    final picked = await _picker.pickImage(
      source: ImageSource.camera,
      preferredCameraDevice: CameraDevice.front,
      imageQuality: 85,
    );
    if (picked == null) return;
    setState(() {
      _captures[_steps[_currentStep].key] = File(picked.path);
      _error = null;
      if (_currentStep < _steps.length - 1) {
        _currentStep += 1;
      }
    });
  }

  Future<void> _submit() async {
    final front = _captures['front'];
    final left = _captures['left'];
    final right = _captures['right'];
    if (front == null || left == null || right == null) {
      setState(() => _error = 'Completa las tres capturas antes de enviar.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final result = await widget.apiClient.registerMobileFaceProfile(
        token: widget.token,
        frontFile: front,
        leftFile: left,
        rightFile: right,
      );
      widget.onCompleted(result);
    } on FaceApiException catch (error) {
      setState(() => _error = error.body);
    } catch (error) {
      setState(() => _error = 'No se pudo registrar el rostro: $error');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final step = _steps[_currentStep];
    final currentFile = _captures[step.key];
    final allDone = _captures.values.every((file) => file != null);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Registro facial'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: widget.onBack,
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                step.title,
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(step.hint),
              const SizedBox(height: 8),
              Text(
                'Paso ${_currentStep + 1} de ${_steps.length}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 20),
              Expanded(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.blueGrey.shade200),
                    borderRadius: BorderRadius.circular(16),
                    color: Colors.blueGrey.shade50,
                  ),
                  child: currentFile == null
                      ? const Center(child: Icon(Icons.face_retouching_natural, size: 72))
                      : ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: Image.file(currentFile, fit: BoxFit.cover),
                        ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: _steps.map((item) {
                  final done = _captures[item.key] != null;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: LinearProgressIndicator(
                        value: done ? 1 : 0,
                        minHeight: 6,
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  );
                }).toList(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 16),
              if (!allDone)
                FilledButton(
                  onPressed: _submitting ? null : _captureCurrent,
                  child: Text(currentFile == null ? 'Tomar foto' : 'Repetir y continuar'),
                ),
              if (allDone)
                FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: _submitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Enviar registro facial'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CaptureStep {
  const _CaptureStep({
    required this.key,
    required this.title,
    required this.hint,
  });

  final String key;
  final String title;
  final String hint;
}
