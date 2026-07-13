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

## Gmail (token por correo — obligatorio en produccion)

El trabajador recibe el token **solo por Gmail**. En Render no existe `backend/token.json` a menos que lo configures.

### Paso 1: generar token.json en tu PC (una vez)

En la carpeta `backend/`:

1. Descarga `credentials.json` desde Google Cloud Console (API Gmail + OAuth desktop).
2. Ejecuta: `python generar_token.py` (abre el navegador, autoriza la cuenta que enviara los correos).
3. Se crea `backend/token.json` (no se sube a Git).

### Paso 2: subir el token a Render

**Opcion A — Secret File (recomendada)**

1. Render → tu Web Service → **Environment** → **Secret Files**
2. **Add Secret File**
   - Filename: `token.json`
   - Contents: pega todo el contenido de tu `backend/token.json` local
3. Agrega variable de entorno:

| Key | Value |
|-----|-------|
| `GMAIL_TOKEN_PATH` | `/etc/secrets/token.json` |

**Opcion B — variable de entorno**

| Key | Value |
|-----|-------|
| `GMAIL_TOKEN_JSON` | contenido completo del JSON en una linea |

### Paso 3: produccion

| Key | Value |
|-----|-------|
| `ENVIRONMENT` | `production` |
| `EXPOSE_DEV_REGISTRATION_TOKEN` | `false` |

En produccion el API **no** devuelve `dev_token`; el token solo va al correo del trabajador.
Si ves `No se pudo refrescar OAuth de Gmail: HTTP 400`, el `token.json` de Gmail fue
revocado, vencio o no corresponde a `credentials.json`: vuelve a generar `backend/token.json`,
subelo al servidor y reinicia el backend.

### Paso 4: probar

1. Redeploy en Render.
2. En el dashboard, **reenvia token** al trabajador (o crea uno nuevo).
3. Debe llegar el correo a la bandeja del trabajador (revisa spam).

Si falla, el mensaje dira el motivo (token ausente, OAuth invalido, etc.).

## Plan recomendado

Al menos **2 GB RAM** para DeepFace + TensorFlow.
