# IA Facial Mobile

App Flutter para registro facial masivo mediante token enviado por RRHH.

## Flujo

1. **Token**: el trabajador ingresa el token recibido por Gmail.
2. **Datos**: la app muestra nombre, codigo, area, cargo y turno (solo lectura).
3. **Capturas**: frontal, giro izquierda y giro derecha.
4. **Confirmacion**: mensaje de registro completado.

La app no permite editar nombre, area, cargo ni turno.

## Ejecutar

```powershell
cd C:\SpringProjectsnew\ia_facial\mobile\flutter_client
flutter pub get
flutter run
```

## URL del backend

- Emulador Android: `http://10.0.2.2:8000`
- Dispositivo fisico: `http://<IP-de-tu-PC>:8000`

La pantalla inicial permite cambiar la URL antes de validar el token.

## APIs usadas

- `POST /api/v1/registration-tokens/validate`
- `POST /api/v1/mobile/faces/register-profile`

El cliente HTTP esta en `lib/api/face_api_client.dart`.
