import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../utils/multipart_image.dart';

class FaceApiClient {
  FaceApiClient({
    required this.baseUrl,
    Duration? timeout,
    Duration? profileUploadTimeout,
  })  : timeout = timeout ?? const Duration(seconds: 90),
        profileUploadTimeout =
            profileUploadTimeout ?? const Duration(minutes: 10);

  final String baseUrl;
  final Duration timeout;
  /// Registro movil: 3 fotos + DeepFace en Render (hasta 10 min).
  final Duration profileUploadTimeout;

  /// Despierta Render con reintentos cortos (no bloquear minutos).
  Future<bool> wakeUpServer({int maxAttempts = 6}) async {
    final uri = Uri.parse('$baseUrl/api/v1/health');
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        final response = await http
            .get(uri)
            .timeout(const Duration(seconds: 25));
        if (response.statusCode == 200) return true;
      } catch (_) {
        // Render cold start: reintentar.
      }
      if (attempt < maxAttempts - 1) {
        await Future<void>.delayed(const Duration(seconds: 2));
      }
    }
    return false;
  }

  /// Precarga IA en segundo plano (no bloquea el envio).
  Future<bool> warmAiModels({Duration? maxWait}) async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/health/ai');
      final response = await http
          .get(uri)
          .timeout(maxWait ?? const Duration(minutes: 3));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> identifyFace(File imageFile) async {
    final uri = Uri.parse('$baseUrl/api/v1/faces/identify');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('file', imageFile.path));

    final streamed = await request.send().timeout(timeout);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FaceApiException(
        statusCode: response.statusCode,
        body: response.body,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> registerFace({
    required String personId,
    required String name,
    required File imageFile,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/faces/register');
    final request = http.MultipartRequest('POST', uri)
      ..fields['person_id'] = personId
      ..fields['name'] = name
      ..files.add(await http.MultipartFile.fromPath('file', imageFile.path));

    final streamed = await request.send().timeout(timeout);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FaceApiException(
        statusCode: response.statusCode,
        body: response.body,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> validateRegistrationToken(String token) async {
    final uri = Uri.parse('$baseUrl/api/v1/registration-tokens/validate');
    final response = await http
        .post(
          uri,
          headers: const {
            'Content-Type': 'application/json',
            'X-Client-Source': 'mobile',
          },
          body: jsonEncode({'token': token.trim()}),
        )
        .timeout(timeout);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FaceApiException(
        statusCode: response.statusCode,
        body: response.body,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> registerMobileFaceProfile({
    required String token,
    required File frontFile,
    required File leftFile,
    required File rightFile,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/mobile/faces/register-profile');
    final request = http.MultipartRequest('POST', uri)
      ..fields['token'] = token.trim()
      ..files.addAll([
        await jpegMultipartFile(field: 'front', file: frontFile, filename: 'front.jpg'),
        await jpegMultipartFile(field: 'left', file: leftFile, filename: 'left.jpg'),
        await jpegMultipartFile(field: 'right', file: rightFile, filename: 'right.jpg'),
      ]);

    final streamed = await request.send().timeout(profileUploadTimeout);
    final response = await http.Response.fromStream(streamed).timeout(
      profileUploadTimeout,
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FaceApiException(
        statusCode: response.statusCode,
        body: response.body,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> completeRegistrationToken(String token) async {
    final uri = Uri.parse('$baseUrl/api/v1/registration-tokens/complete');
    final response = await http
        .post(
          uri,
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode({'token': token.trim()}),
        )
        .timeout(timeout);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FaceApiException(
        statusCode: response.statusCode,
        body: response.body,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> submitExitAttemptWithFace({
    required File imageFile,
    DateTime? attemptedAt,
    String? scheduledExitTime,
    int? toleranceMinutes,
    String? reason,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/attendance/exit-attempts/with-face');
    final request = http.MultipartRequest('POST', uri)
      ..fields['source'] = 'android'
      ..files.add(await http.MultipartFile.fromPath('file', imageFile.path));

    if (attemptedAt != null) {
      request.fields['attempted_at'] = attemptedAt.toIso8601String();
    }
    if (scheduledExitTime != null) {
      request.fields['scheduled_exit_time'] = scheduledExitTime;
    }
    if (toleranceMinutes != null) {
      request.fields['tolerance_minutes'] = toleranceMinutes.toString();
    }
    if (reason != null && reason.trim().isNotEmpty) {
      request.fields['reason'] = reason.trim();
    }

    final streamed = await request.send().timeout(timeout);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw FaceApiException(
        statusCode: response.statusCode,
        body: response.body,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}

class FaceApiException implements Exception {
  FaceApiException({required this.statusCode, required this.body});

  final int statusCode;
  final String body;

  String get detail => FaceApiErrorParser.detailFromBody(body);

  bool get isDuplicateFace => FaceApiErrorParser.isDuplicateFace(
        statusCode: statusCode,
        body: body,
      );

  @override
  String toString() => 'FaceApiException($statusCode): $body';
}

class FaceApiErrorParser {
  static String detailFromBody(String body) {
    final text = body.trim();
    if (text.isEmpty) return 'Error desconocido del servidor.';

    try {
      final decoded = jsonDecode(text);
      if (decoded is Map && decoded['detail'] != null) {
        return decoded['detail'].toString();
      }
    } catch (_) {
      // texto plano
    }

    return text;
  }

  static bool isDuplicateFace({
    required int statusCode,
    required String body,
  }) {
    if (statusCode == 409) return true;
    final detail = detailFromBody(body).toLowerCase();
    return detail.contains('ya esta registrado') ||
        detail.contains('ya está registrado');
  }
}
