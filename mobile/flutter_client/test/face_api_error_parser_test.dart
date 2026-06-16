import 'package:flutter_test/flutter_test.dart';
import 'package:ia_facial_mobile/api/face_api_client.dart';

void main() {
  test('detecta rostro duplicado por codigo 409', () {
    expect(
      FaceApiErrorParser.isDuplicateFace(
        statusCode: 409,
        body: '{"detail":"conflicto"}',
      ),
      isTrue,
    );
  });

  test('detecta rostro duplicado por mensaje del servidor', () {
    const body =
        '{"detail":"Este rostro ya esta registrado como Carlos (FN-CF-0001)."}';

    expect(
      FaceApiErrorParser.isDuplicateFace(statusCode: 422, body: body),
      isTrue,
    );
    expect(
      FaceApiErrorParser.detailFromBody(body),
      contains('Carlos'),
    );
  });
}
