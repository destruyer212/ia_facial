# Flujo Android -> API -> IA

Android no ejecuta Python. Android consume la API Python por HTTP.

```mermaid
sequenceDiagram
    participant App as Flutter Android
    participant API as FastAPI
    participant CV as OpenCV
    participant AI as DeepFace
    participant DB as Embeddings

    App->>API: POST /api/v1/faces/identify multipart image
    API->>API: valida tipo y tamano
    API->>CV: lee imagen / preprocesa
    API->>AI: genera embedding
    AI-->>API: vector facial
    API->>DB: busca embedding mas cercano
    DB-->>API: candidato y distancia
    API-->>App: matched, candidate, threshold
```

## Flujo de salida laboral inteligente

```mermaid
sequenceDiagram
    participant App as Flutter Android
    participant API as FastAPI
    participant Face as DeepFace
    participant Rules as Reglas
    participant AI as IA motivo
    participant Alert as Supervisor

    App->>API: POST /attendance/exit-attempts/with-face
    API->>Face: identificar rostro
    Face-->>API: empleado
    API->>Rules: validar scheduled_exit_time y tolerancia
    Rules-->>API: requiere motivo o permite salida
    App->>API: reintenta con motivo si aplica
    API->>AI: analiza motivo
    AI-->>API: valido/invalido
    API->>Alert: notifica si hay incidencia
    API-->>App: decision final
```

## URL local desde Android

Si pruebas en emulador Android:

- API en PC: `http://127.0.0.1:8000`
- Desde emulador Android: `http://10.0.2.2:8000`

Si pruebas en celular fisico:

- Usa la IP LAN de tu PC, por ejemplo `http://192.168.1.50:8000`
- Ejecuta FastAPI con `--host 0.0.0.0`

## Ejemplo

Ver [face_api_client.dart](C:/SpringProjectsnew/ia_facial/mobile/flutter_client/lib/api/face_api_client.dart).

## Reglas practicas

- Comprimir imagen antes de enviar.
- Evitar enviar video continuo en MVP.
- Enviar una captura clara por intento.
- Mostrar resultado y pedir reintento si no hay rostro.
- No guardar fotos en Android sin consentimiento.
- El horario enviado desde Android debe venir del turno activo, no hardcodeado en la app.
