# Fases: núcleo IA facial + liveness

Roadmap para llevar el MVP actual a nivel empresarial.

## Estado actual (MVP)

| Componente | Hoy |
|------------|-----|
| Detección | OpenCV Haar |
| Embeddings | DeepFace Facenet512 |
| Registro | 1 foto por persona |
| Liveness | No |
| Storage | Supabase + R2 (configurable) |

---

## Fase 1 — Registro facial robusto ✅ (implementada en esta iteración)

**Objetivo:** no depender de una sola foto.

### Capturas requeridas

| Pose | Campo | Obligatorio |
|------|--------|-------------|
| Frontal | `front` | Sí |
| Giro izquierda | `left` | Sí |
| Giro derecha | `right` | Sí |
| Con lentes | `with_glasses` | No |
| Sin lentes | `without_glasses` | No |

### Qué se guarda

- **1 embedding por pose** (vector 512) en `face_embeddings.metadata.pose_type`
- **Foto principal** (frontal) en R2 + `face_assets`
- Fotos extra en R2 bajo `person/<id>/poses/<pose>.jpg`

### API

```
POST /api/v1/faces/register-profile
  Form: person_id, name, email?, front, left?, right?, with_glasses?, without_glasses?
```

### UI

Menú **Registrar rostro** → formulario con 5 slots de foto + instrucciones.

---

## Fase 2 — Liveness básico ✅ (base implementada)

**Objetivo:** reducir foto en celular / pantalla.

### Flujo en escaneo

1. Mire a la cámara
2. Gire un poco la cabeza
3. Parpadee o acerque el rostro
4. Validando rostro real…
5. Identificación + asistencia

### Validaciones (v1)

- 3 fotos consecutivas de la misma persona (embeddings similares)
- Movimiento de rostro entre fotos (caja facial desplazada)
- Una sola cara por foto

### API

```
POST /api/v1/faces/liveness/verify
  Form: step_front, step_movement, step_blink
```

### Próximo (Fase 2b) ✅ implementada

- MediaPipe Face Mesh (parpadeo EAR, landmarks, giro yaw)
- Textura facial basica (varianza Laplacian — anti-foto simple)
- Umbrales configurables en `.env`

---

## Fase 2b — MediaPipe + textura ✅

| Check | Metodo |
|-------|--------|
| Parpadeo | EAR (Eye Aspect Ratio) paso 3 vs paso 1 |
| Ojos abiertos | EAR frontal >= `LIVENESS_EAR_OPEN_MIN` |
| Giro cabeza | yaw proxy + desplazamiento caja facial |
| Anti-foto simple | `texture_score` (Laplacian en region facial) |
| Misma persona | embeddings entre los 3 frames |

Variables `.env`: `LIVENESS_EAR_BLINK_MAX`, `LIVENESS_EAR_OPEN_MIN`, `LIVENESS_MIN_HEAD_YAW_DELTA`, `LIVENESS_MIN_TEXTURE_SCORE`, `LIVENESS_MIN_PASS_SCORE`.

---

## Fase 3 — Motor ArcFace / InsightFace ✅ (implementada)

**Objetivo:** precisión empresarial.

| Paso | Estado |
|------|--------|
| 3.1 | `insightface` + modelo `buffalo_l` |
| 3.2 | Abstracción `FaceEngine` (DeepFace \| InsightFace) |
| 3.3 | Re-embeddings masivos al cambiar motor (manual: re-registrar perfiles) |
| 3.4 | Benchmark Facenet512 vs ArcFace en tu dataset (pendiente) |

Variable `.env`:

```env
FACE_ENGINE=arcface          # deepface | arcface | insightface
INSIGHTFACE_MODEL=buffalo_l  # solo si FACE_ENGINE=insightface
```

| Motor | Plataforma | Modelo guardado en BD |
|-------|------------|------------------------|
| `deepface` | Todas | `Facenet512` (default) |
| `arcface` | Todas (recomendado Windows) | `ArcFace` |
| `insightface` | Linux / WSL / Windows+MSVC | `arcface_buffalo_l` |

**Importante:** al cambiar de `deepface` a `insightface`, el campo `model` en BD cambia (`Facenet512` → `arcface_buffalo_l`). Debes **re-registrar** los perfiles faciales.

Diagnóstico: `GET /api/v1/health/ai`

---

## Fase 4 — Anti-spoofing avanzado ✅ (implementada)

| Tecnología | Uso |
|------------|-----|
| MediaPipe Face Mesh | Parpadeo (EAR), sonrisa/boca (MAR) |
| Anti-spoof heurístico | FFT + color HSV + contraste (print/replay) |
| Desafío aleatorio | `GET /liveness/challenge` — orden impredecible |
| Score compuesto | Ponderado >= `0.85` (`LIVENESS_MIN_PASS_SCORE`) |
| Auditoría | Tabla `liveness_checks` (migración v2) |

### API

```
GET  /api/v1/faces/liveness/challenge
POST /api/v1/faces/liveness/verify
  Form: challenge_id?, person_id?, step_front, step_movement, step_blink, step_smile?
```

### Migración Supabase

Ejecutar `infra/supabase/migrations/v2_liveness_checks.sql` en el SQL Editor.

### Variables `.env` (Fase 4)

```env
LIVENESS_MIN_ANTI_SPOOF_SCORE=0.55
LIVENESS_MIN_PASS_SCORE=0.85
LIVENESS_MAR_OPEN_MIN=0.28
LIVENESS_SMILE_ENABLED=true
```

---

## Orden recomendado de ejecución

```
Fase 1 (multi-pose)  →  Fase 2 (liveness v1)  →  Fase 3 (ArcFace)  →  Fase 4 (anti-spoof)
         ↑                        ↑
    ya en código            ya en código
```

## No requiere tablas nuevas (Fase 1–2)

- Multi-pose usa `face_embeddings.metadata.pose_type` (JSONB existente)
- Liveness v1 es stateless (sin BD); Fase 4 puede añadir `liveness_checks`
