# Deploy backend en Render

## Python 3.11 (obligatorio)

TensorFlow/DeepFace **no funcionan** con Python 3.14.

En Render → tu **Web Service** → **Environment** → agrega:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11.9` |

Guarda y haz **Manual Deploy** → Deploy latest commit.

En los logs debe aparecer:

```text
Using Python version 3.11.9
```

**No** `3.14.3`.

## Configuracion del servicio

| Campo | Valor |
|-------|-------|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

## Variables de entorno minimas

Copia desde tu `backend/.env` local (no subas el archivo a Git):

- `STORAGE_BACKEND=supabase`
- `DATABASE_URL=...` (Supabase Session pooler)
- `DEFAULT_ORG_CODE=demo`
- R2 y demas segun tu `.env`

## MediaPipe (liveness)

El codigo usa `mediapipe.solutions.face_mesh`. Esa API **no existe** desde MediaPipe **0.10.30**.
En `requirements.txt` debe estar `mediapipe==0.10.21`.

Si el deploy falla con `AttributeError: module 'mediapipe' has no attribute 'solutions'`, redeploya
con el commit que fija esa version.

## Plan recomendado

Al menos **2 GB RAM** para DeepFace + TensorFlow.
