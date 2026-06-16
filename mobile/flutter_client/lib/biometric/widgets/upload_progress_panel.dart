import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';

import '../../api/face_api_client.dart';
import '../../theme/app_theme.dart';
import '../../utils/upload_image.dart';

/// Panel de progreso mientras se suben las 3 capturas al servidor.
class UploadProgressPanel extends StatefulWidget {
  const UploadProgressPanel({
    super.key,
    required this.apiClient,
    required this.token,
    required this.frontFile,
    required this.leftFile,
    required this.rightFile,
    required this.onSuccess,
    required this.onError,
  });

  final FaceApiClient apiClient;
  final String token;
  final File frontFile;
  final File leftFile;
  final File rightFile;
  final ValueChanged<Map<String, dynamic>> onSuccess;
  final void Function(String body, {bool duplicateFace}) onError;

  @override
  State<UploadProgressPanel> createState() => _UploadProgressPanelState();
}

class _UploadProgressPanelState extends State<UploadProgressPanel> {
  Timer? _timer;
  int _elapsedSec = 0;
  String _status = 'Preparando fotos...';
  bool _running = true;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _elapsedSec++);
    });
    _runUpload();
  }

  Future<void> _runUpload() async {
    try {
      setState(() => _status = 'Despertando servidor...');
      final awake = await widget.apiClient.wakeUpServer();
      if (!mounted) return;

      setState(() => _status = awake
          ? 'Comprimiendo y subiendo fotos...'
          : 'Servidor lento. Sigue esperando...');

      final prepared = await prepareProfileUploads(
        front: widget.frontFile,
        left: widget.leftFile,
        right: widget.rightFile,
      );

      if (!mounted) return;
      setState(() => _status = 'Procesando rostros en servidor...');

      final result = await widget.apiClient.registerMobileFaceProfile(
        token: widget.token,
        frontFile: prepared[0],
        leftFile: prepared[1],
        rightFile: prepared[2],
      );

      if (!mounted) return;
      widget.onSuccess(result);
    } on FaceApiException catch (e) {
      if (mounted) {
        widget.onError(e.body, duplicateFace: e.isDuplicateFace);
      }
    } catch (e) {
      if (mounted) widget.onError(e.toString());
    } finally {
      _running = false;
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final minutes = _elapsedSec ~/ 60;
    final seconds = _elapsedSec % 60;
    final clock = minutes > 0
        ? '${minutes}m ${seconds.toString().padLeft(2, '0')}s'
        : '${seconds}s';

    return Column(
      children: [
        const LinearProgressIndicator(
          color: Color(0xFF38BDF8),
          backgroundColor: Color(0xFF1A2740),
        ),
        const SizedBox(height: 12),
        Text(
          _status,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Color(0xFFF8FAFC),
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Tiempo: $clock · No cierres la app',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: AppColors.textMuted.withValues(alpha: 0.95),
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'La primera vez puede tardar 2-5 min (Render + IA).',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Color(0xFF94A3B8),
            fontSize: 11,
            height: 1.35,
          ),
        ),
        if (_running && _elapsedSec > 45)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Sigue en proceso. Timeout maximo: 10 min.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: AppColors.accent.withValues(alpha: 0.9),
                fontSize: 11,
              ),
            ),
          ),
      ],
    );
  }
}
