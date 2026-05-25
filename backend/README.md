# Backend FastAPI - IA Facial

Backend MVP para reconocimiento facial empresarial.

## Instalacion local en Windows

```powershell
cd C:\SpringProjectsnew\ia_facial\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Probar endpoints

Swagger:

```text
http://127.0.0.1:8000/docs
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Detectar rostro:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/faces/detect" -F "file=@C:\ruta\persona.jpg"
```

Registrar rostro:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/faces/register" -F "person_id=EMP-001" -F "name=Carlos Demo" -F "file=@C:\ruta\persona.jpg"
```

Identificar rostro:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/faces/identify" -F "file=@C:\ruta\otra_foto.jpg"
```

Evaluar salida laboral:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/v1/attendance/exit-attempts" -ContentType "application/json" -Body '{"person_id":"EMP-001","employee_name":"Carlos Demo","attempted_at":"2026-05-24T21:35:00-05:00","scheduled_exit_time":"22:00:00","tolerance_minutes":10,"reason":"Tengo una emergencia familiar","source":"android"}'
```

Registrar evento de asistencia desde edge:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/v1/attendance/events" -ContentType "application/json" -Body '{"person_id":"EMP-001","employee_name":"Carlos Demo","device_id":"edge-windows-001","event_type":"check_in","confidence":0.98,"captured_at":"2026-05-24T08:00:00-05:00","source":"edge"}'
```

## Nota tecnica

DeepFace puede descargar modelos la primera vez que se ejecuta un endpoint de IA. El arranque de `health` no importa DeepFace, para que el backend pueda iniciar rapido y fallar de forma controlada si faltan dependencias pesadas.
