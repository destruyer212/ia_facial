import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api/face_api_client.dart';
import '../controllers/live_face_register_controller.dart';
import '../models/register_scan_step.dart';
import '../theme/app_theme.dart';
import '../utils/responsive.dart';
import '../widgets/face_scan_overlay.dart';

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
  late final LiveFaceRegisterController _scanner;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _scanner = LiveFaceRegisterController();
    _scanner.addListener(_onScannerChanged);
    _scanner.initialize();
  }

  void _onScannerChanged() {
    if (_scanner.phase == ScanPhase.done && mounted && !_submitting) {
      _submitCaptures();
    }
    setState(() {});
  }

  Future<void> _submitCaptures() async {
    if (_submitting) return;
    _submitting = true;
    final front = _scanner.captures['front'];
    final left = _scanner.captures['left'];
    final right = _scanner.captures['right'];
    if (front == null || left == null || right == null) return;

    _scanner.markSubmitting();
    try {
      final result = await widget.apiClient.registerMobileFaceProfile(
        token: widget.token,
        frontFile: front,
        leftFile: left,
        rightFile: right,
      );
      if (mounted) widget.onCompleted(result);
    } on FaceApiException catch (error) {
      _scanner.phase = ScanPhase.error;
      _scanner.errorMessage = error.body;
      _scanner.statusHint = error.body;
    } catch (error) {
      _scanner.phase = ScanPhase.error;
      _scanner.errorMessage = 'No se pudo registrar el rostro: $error';
      _scanner.statusHint = _scanner.errorMessage ?? 'Error de registro';
    }
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _scanner.removeListener(_onScannerChanged);
    _scanner.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.worker['name'] as String? ?? 'Trabajador';
    final camera = _scanner.cameraController;
    final showErrorButton = _scanner.phase == ScanPhase.error;
    final bottomReserved = AppResponsive.scanBottomReserved(
      context,
      showErrorButton: showErrorButton,
    );
    final topReserved = AppResponsive.scanTopReserved(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: AppColors.background,
        resizeToAvoidBottomInset: false,
        body: Stack(
          fit: StackFit.expand,
          children: [
            if (camera != null && camera.value.isInitialized)
              _buildCameraPreview(camera)
            else
              const ColoredBox(
                color: AppColors.background,
                child: Center(
                  child: CircularProgressIndicator(color: AppColors.accent),
                ),
              ),
            if (camera != null && camera.value.isInitialized)
              LayoutBuilder(
                builder: (context, constraints) {
                  final canvasSize = Size(constraints.maxWidth, constraints.maxHeight);
                  final geometry = GuideCircleGeometry(
                    size: canvasSize,
                    topReserved: topReserved,
                    bottomReserved: bottomReserved,
                  );
                  _scanner.updateScanTargets(
                    canvas: canvasSize,
                    center: geometry.center,
                    radius: geometry.radius,
                  );

                  return FaceScanOverlay(
                    metrics: _scanner.latestMetrics,
                    canvasSize: canvasSize,
                    imageSize: _scanner.imageSize,
                    rotation: _scanner.imageRotation,
                    lensDirection: camera.description.lensDirection,
                    aligned: _scanner.aligned,
                    poseOk: _scanner.poseOk,
                    stepIndex: _scanner.stepIndex,
                    topReserved: topReserved,
                    bottomReserved: bottomReserved,
                  );
                },
              ),
            _buildChrome(name, showErrorButton),
          ],
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

  Widget _buildChrome(String name, bool showErrorButton) {
    final step = registerScanSteps[_scanner.stepIndex];
    final stepLabel =
        'Paso ${_scanner.stepIndex + 1}/${registerScanSteps.length}: ${step.label}';
    final horizontal = AppResponsive.horizontalPadding(context);

    return SafeArea(
      child: Column(
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(4, 4, 4, 0),
            child: Row(
              children: [
                IconButton(
                  onPressed: _scanner.phase == ScanPhase.submitting ? null : widget.onBack,
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
                        'Registro facial automatico',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
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
                  ScanStepChips(
                    stepIndex: _scanner.stepIndex,
                    captures: _scanner.captures,
                  ),
                  const SizedBox(height: 12),
                  ScanStatusCard(
                    title: _scanner.statusTitle,
                    hint: _scanner.errorMessage ?? _scanner.statusHint,
                    stepLabel: stepLabel,
                  ),
                  if (showErrorButton) ...[
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        onPressed: () {
                          _submitting = false;
                          _scanner.resetAndRestart();
                        },
                        child: const Text('Reintentar escaneo'),
                      ),
                    ),
                  ],
                  if (_scanner.phase == ScanPhase.submitting) ...[
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
