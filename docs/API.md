# API recomendada

## MVP implementado

### Health

`GET /api/v1/health`

Sirve para verificar que el backend esta vivo sin cargar modelos de IA.

### Detectar rostros

`POST /api/v1/faces/detect`

`multipart/form-data`:

- `file`: JPG, PNG o WEBP.

Respuesta:

```json
{
  "image_width": 1280,
  "image_height": 720,
  "face_count": 1,
  "faces": [{ "x": 100, "y": 120, "width": 180, "height": 180 }]
}
```

### Analizar rostro

`POST /api/v1/faces/analyze`

Usa DeepFace para edad, genero, emocion y raza. En produccion, usa este endpoint con cuidado porque puede introducir riesgos eticos, legales y de sesgo.

### Crear embedding

`POST /api/v1/faces/embedding`

Devuelve tamano del vector y una vista parcial. En produccion no se deben devolver embeddings completos al cliente.

### Registrar rostro

`POST /api/v1/faces/register`

`multipart/form-data`:

- `person_id`
- `name`
- `file`

### Identificar rostro

`POST /api/v1/faces/identify`

Compara una imagen contra embeddings registrados en el storage local.

### Listar registrados

`GET /api/v1/faces/registered`

Devuelve metadata publica, no embeddings.

## Control laboral MVP

### Politica activa

`GET /api/v1/attendance/policy`

Devuelve la politica por defecto del entorno local. En produccion se resuelve por empresa, sede, turno o empleado.

### Evaluar salida

`POST /api/v1/attendance/exit-attempts`

Ejemplo:

```json
{
  "person_id": "EMP-001",
  "employee_name": "Carlos Demo",
  "attempted_at": "2026-05-24T21:35:00-05:00",
  "scheduled_exit_time": "22:00:00",
  "tolerance_minutes": 10,
  "reason": "Tengo una emergencia familiar",
  "source": "android"
}
```

### Evaluar salida con rostro

`POST /api/v1/attendance/exit-attempts/with-face`

`multipart/form-data`:

- `file`: imagen del rostro.
- `attempted_at`: fecha/hora ISO opcional.
- `scheduled_exit_time`: horario de salida del turno, opcional.
- `tolerance_minutes`: tolerancia, opcional.
- `reason`: motivo escrito, opcional.
- `source`: android, kiosk, web.

### Incidencias

`GET /api/v1/attendance/incidents`

Filtros:

- `person_id`
- `limit`

### Evento de asistencia desde edge

`POST /api/v1/attendance/events`

El dispositivo local envia un evento pequeno despues de reconocer a una persona. No envia video continuo.

```json
{
  "person_id": "EMP-001",
  "employee_name": "Carlos Demo",
  "device_id": "edge-windows-001",
  "event_type": "check_in",
  "confidence": 0.98,
  "captured_at": "2026-05-24T08:00:00-05:00",
  "source": "edge"
}
```

### Listar eventos de asistencia

`GET /api/v1/attendance/events`

Filtros:

- `person_id`
- `device_id`
- `limit`

## API futura profesional

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/me`
- `POST /api/v1/organizations`
- `GET /api/v1/people`
- `POST /api/v1/people`
- `GET /api/v1/people/{id}`
- `POST /api/v1/people/{id}/face-enrollments`
- `POST /api/v1/recognition/identify`
- `GET /api/v1/recognition/events`
- `GET /api/v1/audit/events`
- `POST /api/v1/schedules`
- `POST /api/v1/people/{id}/schedule-assignments`
- `GET /api/v1/behavior/{person_id}`

## Autenticacion

Fase 1:

- Sin auth para desarrollo local.

Fase 2:

- JWT access token corto.
- Refresh token seguro.
- Roles: `owner`, `admin`, `operator`, `viewer`.
- Todas las consultas filtradas por `organization_id`.

## Manejo de usuarios

Modelo recomendado:

- Organization: empresa cliente.
- User: quien usa el sistema.
- Person: persona reconocible.
- FaceEmbedding: vectores de una persona.
- RecognitionEvent: evento de reconocimiento.
