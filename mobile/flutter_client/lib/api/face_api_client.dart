import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

class FaceApiClient {
  FaceApiClient({required this.baseUrl, Duration? timeout})
      : timeout = timeout ?? const Duration(seconds: 90);

  final String baseUrl;
  final Duration timeout;

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
      ..files.add(await http.MultipartFile.fromPath('front', frontFile.path))
      ..files.add(await http.MultipartFile.fromPath('left', leftFile.path))
      ..files.add(await http.MultipartFile.fromPath('right', rightFile.path));

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

  @override
  String toString() => 'FaceApiException($statusCode): $body';
}
