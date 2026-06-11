import 'package:flutter_test/flutter_test.dart';
import 'package:ia_facial_mobile/main.dart';

void main() {
  testWidgets('muestra pantalla de token', (WidgetTester tester) async {
    await tester.pumpWidget(const IaFacialMobileApp());
    expect(find.text('Ingresa tu token'), findsOneWidget);
    expect(find.text('Validar token'), findsOneWidget);
  });
}
