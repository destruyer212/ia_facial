import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api/face_api_client.dart';
import 'config/api_config.dart';
import 'screens/confirmation_screen.dart';
import 'screens/face_capture_screen.dart';
import 'screens/token_screen.dart';
import 'screens/worker_data_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
  ]);
  runApp(const IaFacialMobileApp());
}

class IaFacialMobileApp extends StatelessWidget {
  const IaFacialMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'IA Facial Enterprise',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark(),
      home: const TokenRegistrationFlow(),
    );
  }
}

class TokenRegistrationFlow extends StatefulWidget {
  const TokenRegistrationFlow({super.key});

  @override
  State<TokenRegistrationFlow> createState() => _TokenRegistrationFlowState();
}

enum _RegistrationStep { token, workerData, capture, confirmation }

class _TokenRegistrationFlowState extends State<TokenRegistrationFlow> {
  static const _defaultBaseUrl = kProductionApiBaseUrl;

  late FaceApiClient _apiClient = FaceApiClient(baseUrl: _defaultBaseUrl);
  String _baseUrl = _defaultBaseUrl;
  _RegistrationStep _step = _RegistrationStep.token;
  String? _token;
  Map<String, dynamic>? _worker;
  Map<String, dynamic>? _registrationResult;

  void _restart() {
    setState(() {
      _step = _RegistrationStep.token;
      _token = null;
      _worker = null;
      _registrationResult = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_step == _RegistrationStep.confirmation && _registrationResult != null) {
      return ConfirmationScreen(
        message: _registrationResult!['storage_message'] as String? ??
            'Registro facial completado correctamente.',
        worker: _worker,
        onFinish: _restart,
      );
    }

    if (_step == _RegistrationStep.capture && _worker != null && _token != null) {
      return FaceCaptureScreen(
        apiClient: _apiClient,
        token: _token!,
        worker: _worker!,
        onCompleted: (result) {
          setState(() {
            _registrationResult = result;
            _step = _RegistrationStep.confirmation;
          });
        },
        onBack: () => setState(() => _step = _RegistrationStep.workerData),
      );
    }

    if (_step == _RegistrationStep.workerData && _worker != null) {
      return WorkerDataScreen(
        worker: _worker!,
        onContinue: () => setState(() => _step = _RegistrationStep.capture),
        onBack: _restart,
      );
    }

    return TokenScreen(
      baseUrl: _baseUrl,
      onBaseUrlChanged: (value) {
        setState(() {
          _baseUrl = value.trim();
          _apiClient = FaceApiClient(baseUrl: _baseUrl);
        });
      },
      onValidated: (token, worker) {
        setState(() {
          _token = token;
          _worker = worker;
          _step = _RegistrationStep.workerData;
        });
      },
    );
  }
}
