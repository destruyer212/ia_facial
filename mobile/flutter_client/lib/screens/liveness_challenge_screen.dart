import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

import '../api/face_api_client.dart';
import '../theme/app_theme.dart';
import '../utils/responsive.dart';

class LivenessChallengeScreen extends StatefulWidget {
  const LivenessChallengeScreen({
    super.key,
    required this.apiClient,
    required this.workerName,
    required this.onPassed,
    required this.onBack,
  });

  final FaceApiClient apiClient;
  final String workerName;
  final VoidCallback onPassed;
  final VoidCallback onBack;

  @override
  State<LivenessChallengeScreen> createState() => _LivenessChallengeScreenState();
}

class _LivenessChallengeScreenState extends State<LivenessChallengeScreen> {
  CameraController? _camera;
  List<Map<String, dynamic>> _steps = [];
  String? _challengeId;
  int _stepIndex = 0;
  int? _countdown;
  bool _loading = true;
  bool _capturing = false;
  bool _verifying = false;
  String? _error;
  String _hint = 'Preparando prueba de vida...';
  final Map<String, File> _captures = {};

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final permission = await Permission.camera.request();
    if (!permission.isGranted) {
      setState(() {
        _loading = false;
        _error = 'Se necesita permiso de camara para validar que eres una persona real.';
      });
      return;
    }

    try {
      await widget.apiClient.wakeUpServer();
      final challenge = await widget.apiClient.getLivenessChallenge();
      final cameras = await availableCameras();
      final front = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        front,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: Platform.isAndroid
            ? ImageFormatGroup.nv21
            : ImageFormatGroup.bgra8888,
      );
      await controller.initialize();

      final steps = (challenge['steps'] as List<dynamic>? ?? [])
          .cast<Map<String, dynamic>>();

      if (!mounted) {
        await controller.dispose();
        return;
      }

      setState(() {
        _camera = controller;
        _challengeId = challenge['challenge_id'] as String?;
        _steps = steps;
        _loading = false;
        _hint = _currentPrompt();
      });

      await _runCountdownAndCapture();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = _humanizeError(error);
      });
    }
  }

  String _currentPrompt() {
    if (_steps.isEmpty) return 'Mira a la camara';
    return _steps[_stepIndex]['prompt'] as String? ?? 'Mira a la camara';
  }

  String _stepLabel() {
    if (_steps.isEmpty) return 'Paso 1/1';
    return 'Paso ${_stepIndex + 1}/${_steps.length}';
  }

  Future<void> _runCountdownAndCapture() async {
    if (_camera == null || _verifying) return;

    for (var n = 3; n >= 1; n--) {
      if (!mounted) return;
      setState(() {
        _countdown = n;
        _hint = '${_currentPrompt()}\nPreparate...';
      });
      await HapticFeedback.lightImpact();
      await Future<void>.delayed(const Duration(milliseconds: 900));
    }

    if (!mounted) return;
    setState(() {
      _countdown = null;
      _capturing = true;
      _hint = 'Capturando...';
    });

    try {
      final file = await _camera!.takePicture();
      final step = _steps[_stepIndex];
      final field = step['form_field'] as String;
      _captures[field] = File(file.path);

      if (_stepIndex >= _steps.length - 1) {
        await _verifyAll();
        return;
      }

      setState(() {
        _stepIndex += 1;
        _capturing = false;
        _hint = _currentPrompt();
      });
      await Future<void>.delayed(const Duration(milliseconds: 500));
      await _runCountdownAndCapture();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _capturing = false;
        _error = 'No se pudo capturar: $error';
      });
    }
  }

  Future<void> _verifyAll() async {
    setState(() {
      _verifying = true;
      _hint = 'Validando rostro real en el servidor...';
    });

    try {
      final result = await widget.apiClient.verifyLiveness(
        challengeId: _challengeId,
        stepFiles: _captures,
      );
      final passed = result['passed'] == true;
      if (!passed) {
        final message = result['message'] as String? ??
            'No se valido rostro humano en vivo.';
        setState(() {
          _verifying = false;
          _capturing = false;
          _error = message;
        });
        return;
      }

      await _camera?.dispose();
      _camera = null;
      if (mounted) widget.onPassed();
    } on FaceApiException catch (error) {
      setState(() {
        _verifying = false;
        _capturing = false;
        _error = FaceApiErrorParser.detailFromBody(error.body);
      });
    } catch (error) {
      setState(() {
        _verifying = false;
        _capturing = false;
        _error = _humanizeError(error);
      });
    }
  }

  String _humanizeError(Object error) {
    if (error is FaceApiException) {
      return FaceApiErrorParser.detailFromBody(error.body);
    }
    return error.toString();
  }

  Future<void> _retry() async {
    setState(() {
      _loading = true;
      _error = null;
      _stepIndex = 0;
      _captures.clear();
      _countdown = null;
      _capturing = false;
      _verifying = false;
    });
    await _bootstrap();
  }

  @override
  void dispose() {
    _camera?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final horizontal = AppResponsive.horizontalPadding(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: AppColors.background,
        body: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(4, 4, 4, 0),
                child: Row(
                  children: [
                    IconButton(
                      onPressed: (_capturing || _verifying) ? null : widget.onBack,
                      icon: const Icon(Icons.arrow_back, color: Colors.white),
                    ),
                    Expanded(
                      child: Column(
                        children: [
                          Text(
                            widget.workerName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.textPrimary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const Text(
                            'Prueba de vida',
                            style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 48),
                  ],
                ),
              ),
              Expanded(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(horizontal, 12, horizontal, 0),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(24),
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        if (_camera?.value.isInitialized == true)
                          FittedBox(
                            fit: BoxFit.cover,
                            child: SizedBox(
                              width: _camera!.value.previewSize?.height ?? 1,
                              height: _camera!.value.previewSize?.width ?? 1,
                              child: CameraPreview(_camera!),
                            ),
                          )
                        else
                          const ColoredBox(
                            color: Color(0xFF0B1220),
                            child: Center(
                              child: CircularProgressIndicator(color: AppColors.accent),
                            ),
                          ),
                        if (_countdown != null)
                          ColoredBox(
                            color: Colors.black.withValues(alpha: 0.35),
                            child: Center(
                              child: Text(
                                '$_countdown',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 72,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
              Padding(
                padding: EdgeInsets.fromLTRB(horizontal, 16, horizontal, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      _error != null ? 'Validacion fallida' : _stepLabel(),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: AppColors.accent,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _error ?? _hint,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: AppColors.textMuted,
                        height: 1.4,
                      ),
                    ),
                    if (_loading || _capturing || _verifying) ...[
                      const SizedBox(height: 16),
                      const LinearProgressIndicator(
                        color: AppColors.accent,
                        backgroundColor: AppColors.surfaceLight,
                      ),
                    ],
                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: _retry,
                        child: const Text('Reintentar prueba de vida'),
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton(
                        onPressed: widget.onBack,
                        child: const Text('Volver'),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
