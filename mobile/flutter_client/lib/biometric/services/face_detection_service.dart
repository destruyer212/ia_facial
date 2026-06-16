import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

class FaceDetectionService {
  FaceDetector? _streamDetector;

  Future<void> init() async {
    _streamDetector = FaceDetector(
      options: FaceDetectorOptions(
        enableContours: false,
        enableLandmarks: false,
        enableClassification: true,
        performanceMode: FaceDetectorMode.fast,
        minFaceSize: 0.08,
      ),
    );
  }

  Future<List<Face>> detect(InputImage image) =>
      _streamDetector!.processImage(image);

  Future<void> dispose() async {
    await _streamDetector?.close();
    _streamDetector = null;
  }
}
