import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/face_api_client.dart';
import '../biometric/controllers/biometric_scan_controller.dart';
import '../biometric/models/biometric_scan_phase.dart';
import '../biometric/models/biometric_ui_state.dart';
import '../biometric/widgets/biometric_overlay.dart';
import '../biometric/widgets/capture_transition_layer.dart';
import '../biometric/widgets/quality_warning_chip.dart';
import '../biometric/widgets/scan_hint_panel.dart';
import '../biometric/widgets/scan_progress_bar.dart';
import '../models/register_scan_step.dart';
import '../theme/app_theme.dart';
import '../utils/responsive.dart';
import '../biometric/widgets/upload_progress_panel.dart';

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

class _FaceCaptureScreenState extends State<FaceCaptureScreen>
    with WidgetsBindingObserver {
  late final BiometricScanController _scanner;
  bool _submitting = false;
  bool _showUploadPanel = false;
  bool _duplicateFaceBlocked = false;
  int _uploadAttempt = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scanner = BiometricScanController();
    _scanner.uiState.addListener(_onUiChanged);
    _scanner.initialize();
    _warmUpBackendInBackground();
    WidgetsBinding.instance.addPostFrameCallback((_) => _syncDeviceOrientation());
  }

  @override
  void didChangeMetrics() {
    _syncDeviceOrientation();
  }

  void _syncDeviceOrientation() {
    if (!mounted) return;
    final orientation = MediaQuery.orientationOf(context);
    _scanner.updateDeviceOrientation(
      orientation == Orientation.landscape
          ? DeviceOrientation.landscapeLeft
          : DeviceOrientation.portraitUp,
    );
  }

  void _warmUpBackendInBackground() {
    Future<void>(() async {
      await widget.apiClient.wakeUpServer();
      await widget.apiClient.warmAiModels();
    });
  }

  void _onUiChanged() {
    final phase = _scanner.phase;
    if (phase == BiometricScanPhase.done && mounted && !_submitting) {
      _beginUploadAfterScan();
    }
  }

  Future<void> _beginUploadAfterScan() async {
    await _scanner.releaseCamera();
    if (!mounted) return;
    setState(() {});
    await _submitCaptures();
  }

  Future<void> _submitCaptures() async {
    if (_submitting) return;
    final front = _scanner.captures['front'];
    final left = _scanner.captures['left'];
    final right = _scanner.captures['right'];
    if (front == null || left == null || right == null) return;

    _submitting = true;
    _uploadAttempt++;
    _scanner.markSubmitting(
      title: 'Guardando perfil',
      hint: 'Subiendo capturas al servidor...',
    );
    if (mounted) {
      setState(() => _showUploadPanel = true);
    }
  }

  void _onUploadSuccess(Map<String, dynamic> result) {
    _submitting = false;
    _showUploadPanel = false;
    widget.onCompleted(result);
  }

  void _onUploadError(String raw, {bool duplicateFace = false}) {
    _submitting = false;
    _showUploadPanel = false;
    _duplicateFaceBlocked = duplicateFace;
    _scanner.setExternalError(
      _humanizeApiError(raw, duplicateFace: duplicateFace),
      title: duplicateFace ? 'Rostro ya registrado' : 'Error',
    );
    if (mounted) setState(() {});
  }

  bool get _hasAllCaptures {
    final c = _scanner.captures;
    return c.containsKey('front') &&
        c.containsKey('left') &&
        c.containsKey('right');
  }

  Future<void> _retryUploadOnly() async {
    if (_duplicateFaceBlocked) return;
    if (!_hasAllCaptures) {
      _submitting = false;
      _showUploadPanel = false;
      await _scanner.resetAndRestart();
      return;
    }
    await _submitCaptures();
  }

  String _humanizeApiError(String body, {bool duplicateFace = false}) {
    final detail = FaceApiErrorParser.detailFromBody(body);
    if (duplicateFace ||
        FaceApiErrorParser.isDuplicateFace(statusCode: 409, body: body)) {
      return '$detail\n\n'
          'No puedes registrar la misma persona dos veces. '
          'Pide al administrador que use tu perfil existente o elimine el duplicado.';
    }

    final text = body.trim();
    if (text.contains('TimeoutException') || text.contains('timed out')) {
      return 'El servidor tardo mas de lo esperado.\n\n'
          '1. Pulsa "Reintentar envio" (no vuelvas a escanear).\n'
          '2. Espera 2-5 min con buena WiFi.\n'
          '3. Instala la app v1.2.0+3 (timeout 10 min).';
    }
    if (text.contains('SocketException') ||
        text.contains('Failed host lookup') ||
        text.contains('Connection refused')) {
      return 'Sin conexion al servidor. Revisa tu internet o la URL del backend.';
    }
    if (detail.contains('Formato no soportado')) {
      return 'Formato de imagen no valido. Actualiza la app e intenta de nuevo.';
    }
    return detail.replaceFirst('Error registrando rostro movil: 400: ', '');
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _scanner.uiState.removeListener(_onUiChanged);
    _scanner.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.worker['name'] as String? ?? 'Trabajador';

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: AppColors.background,
        resizeToAvoidBottomInset: false,
        body: ValueListenableBuilder(
          valueListenable: _scanner.uiState,
          builder: (context, ui, _) {
            final camera = _scanner.cameraController;
            final showErrorButton = ui.phase == BiometricScanPhase.error;
            final showCamera = camera != null &&
                camera.value.isInitialized &&
                (ui.phase == BiometricScanPhase.loading ||
                    ui.phase == BiometricScanPhase.scanning ||
                    ui.phase == BiometricScanPhase.capturing);
            final postScan = ui.phase == BiometricScanPhase.done ||
                ui.phase == BiometricScanPhase.submitting ||
                (ui.phase == BiometricScanPhase.error && _hasAllCaptures);
            final bottomReserved = AppResponsive.scanBottomReserved(
              context,
              showErrorButton: showErrorButton,
            );
            final topReserved = AppResponsive.scanTopReserved(context);
            final step = registerScanSteps[ui.stepIndex];
            final stepLabel =
                'Paso ${ui.stepIndex + 1}/${registerScanSteps.length}';

            return Stack(
              fit: StackFit.expand,
              children: [
                if (showCamera)
                  _buildCameraPreview(camera)
                else if (postScan)
                  _buildPostScanBackdrop(ui)
                else
                  const ColoredBox(
                    color: AppColors.background,
                    child: Center(
                      child: CircularProgressIndicator(color: AppColors.accent),
                    ),
                  ),
                if (showCamera)
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final canvasSize = Size(
                        constraints.maxWidth,
                        constraints.maxHeight,
                      );
                      WidgetsBinding.instance.addPostFrameCallback((_) {
                        _scanner.updateLayout(
                          canvas: canvasSize,
                          topReserved: topReserved,
                          bottomReserved: bottomReserved,
                        );
                      });
                      return BiometricOverlay(controller: _scanner);
                    },
                  ),
                if (showCamera) CaptureTransitionLayer(controller: _scanner),
                _buildChrome(
                  name: name,
                  ui: ui,
                  step: step,
                  stepLabel: stepLabel,
                  showErrorButton: showErrorButton,
                  postScan: postScan,
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildCameraPreview(CameraController camera) {
    return FittedBox(
      fit: BoxFit.cover,
      child: SizedBox(
        width: camera.value.previewSize?.height ?? 1,
        height: camera.value.previewSize?.width ?? 1,
        child: CameraPreview(camera),
      ),
    );
  }

  Widget _buildPostScanBackdrop(BiometricUiState ui) {
    final isUploading = ui.phase == BiometricScanPhase.submitting;
    return ColoredBox(
      color: AppColors.background,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isUploading ? Icons.cloud_upload_outlined : Icons.verified_outlined,
              size: 72,
              color: isUploading ? AppColors.accent : AppColors.success,
            ),
            const SizedBox(height: 16),
            Text(
              isUploading ? 'Subiendo perfil' : 'Escaneo completo',
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 20,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              isUploading
                  ? 'Procesando en el servidor...'
                  : '3 fotos capturadas correctamente',
              style: TextStyle(
                color: AppColors.textMuted.withValues(alpha: 0.95),
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChrome({
    required String name,
    required BiometricUiState ui,
    required RegisterScanStep step,
    required String stepLabel,
    required bool showErrorButton,
    required bool postScan,
  }) {
    final horizontal = AppResponsive.horizontalPadding(context);
    final title = ui.statusTitle;

    return SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 4, 4, 0),
            child: Row(
              children: [
                IconButton(
                  onPressed: ui.phase == BiometricScanPhase.submitting
                      ? null
                      : widget.onBack,
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                ),
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Verificacion biometrica',
                        style: TextStyle(
                          color: AppColors.textMuted.withValues(alpha: 0.9),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 48),
              ],
            ),
          ),
          if (ui.warningHint != null)
            Padding(
              padding: EdgeInsets.fromLTRB(horizontal, 8, horizontal, 0),
              child: QualityWarningChip(message: ui.warningHint!),
            ),
          const Spacer(),
          ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.sizeOf(context).height * 0.42,
            ),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(horizontal, 0, horizontal, 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ScanProgressBar(
                    stepIndex: ui.stepIndex,
                    captures: ui.captures,
                  ),
                  const SizedBox(height: 14),
                  ScanHintPanel(
                    stepLabel: postScan && ui.phase != BiometricScanPhase.error
                        ? 'Completado'
                        : stepLabel,
                    title: title,
                    hint: ui.errorMessage ?? ui.statusHint,
                    stabilityProgress: ui.stabilityProgress,
                    transitionKey: '${ui.stepIndex}-${ui.phase.name}',
                  ),
                  if (showErrorButton) ...[
                    const SizedBox(height: 12),
                    if (_hasAllCaptures && !_duplicateFaceBlocked)
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: _submitting ? null : _retryUploadOnly,
                          child: const Text('Reintentar envio'),
                        ),
                      ),
                    if (_hasAllCaptures && !_duplicateFaceBlocked)
                      const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton(
                        onPressed: _submitting
                            ? null
                            : () {
                                _submitting = false;
                                _showUploadPanel = false;
                                _duplicateFaceBlocked = false;
                                _scanner.resetAndRestart();
                              },
                        child: Text(
                          _duplicateFaceBlocked
                              ? 'Volver al inicio'
                              : _hasAllCaptures
                                  ? 'Volver a escanear'
                                  : 'Reintentar escaneo',
                        ),
                      ),
                    ),
                  ],
                  if (_showUploadPanel && _hasAllCaptures) ...[
                    UploadProgressPanel(
                      key: ValueKey('upload-$_uploadAttempt'),
                      apiClient: widget.apiClient,
                      token: widget.token,
                      frontFile: _scanner.captures['front']!,
                      leftFile: _scanner.captures['left']!,
                      rightFile: _scanner.captures['right']!,
                      onSuccess: _onUploadSuccess,
                      onError: (body, {duplicateFace = false}) =>
                          _onUploadError(body, duplicateFace: duplicateFace),
                    ),
                  ] else if (ui.phase == BiometricScanPhase.submitting) ...[
                    const SizedBox(height: 16),
                    const LinearProgressIndicator(
                      color: AppColors.accent,
                      backgroundColor: AppColors.surfaceLight,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
