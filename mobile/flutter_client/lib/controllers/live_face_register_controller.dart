import '../biometric/controllers/biometric_scan_controller.dart';
import '../biometric/models/biometric_scan_phase.dart';

export '../biometric/controllers/biometric_scan_controller.dart';
export '../biometric/models/biometric_scan_phase.dart';

/// Alias legacy para pantallas que aun importen el nombre anterior.
typedef LiveFaceRegisterController = BiometricScanController;
typedef FaceScanController = BiometricScanController;
typedef ScanPhase = BiometricScanPhase;
