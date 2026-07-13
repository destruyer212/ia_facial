import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ia_facial_mobile/screens/token_screen.dart';

void main() {
  testWidgets('muestra pantalla de token', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: TokenScreen(
          baseUrl: 'http://104.238.215.26:8000',
          onBaseUrlChanged: (_) {},
          onValidated: (token, worker) {},
        ),
      ),
    );

    expect(find.text('Ingresa tu token'), findsOneWidget);
    expect(find.text('Validar token'), findsOneWidget);
  });
}
