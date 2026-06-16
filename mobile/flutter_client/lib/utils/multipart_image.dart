import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

/// La camara movil suele enviar application/octet-stream sin extension .jpg.
Future<http.MultipartFile> jpegMultipartFile({
  required String field,
  required File file,
  required String filename,
}) {
  return http.MultipartFile.fromPath(
    field,
    file.path,
    filename: filename.endsWith('.jpg') ? filename : '$filename.jpg',
    contentType: MediaType('image', 'jpeg'),
  );
}
