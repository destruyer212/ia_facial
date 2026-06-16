import 'dart:io';

import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';

/// Normaliza selfies de camara frontal antes de subir:
/// corrige EXIF y espeja para alinear con webcam de PC.
Future<File> prepareUploadJpeg(
  File source, {
  int maxSide = 1280,
  int quality = 82,
  bool mirrorFrontCamera = true,
}) async {
  try {
    final bytes = await source.readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) return source;

    var image = img.bakeOrientation(decoded);
    if (mirrorFrontCamera) {
      image = img.flipHorizontal(image);
    }

    final longest = image.width > image.height ? image.width : image.height;
    final resized = longest > maxSide
        ? img.copyResize(
            image,
            width: image.width >= image.height ? maxSide : null,
            height: image.height > image.width ? maxSide : null,
          )
        : image;

    final dir = await getTemporaryDirectory();
    final out = File(
      '${dir.path}/upload_${DateTime.now().millisecondsSinceEpoch}_${source.uri.pathSegments.last}',
    );
    await out.writeAsBytes(img.encodeJpg(resized, quality: quality));
    return out;
  } catch (_) {
    return source;
  }
}

Future<List<File>> prepareProfileUploads({
  required File front,
  required File left,
  required File right,
}) async {
  return Future.wait([
    prepareUploadJpeg(front),
    prepareUploadJpeg(left),
    prepareUploadJpeg(right),
  ]);
}
