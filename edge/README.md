# Edge Device - Asistencia facial en tiempo real

Este modulo representa el dispositivo local junto a la camara: PC Windows, mini PC, kiosk o tablet futura.

## Principio

Para reconocer en menos de 1 segundo, el video no debe viajar al servidor. El edge device:

1. Captura frames desde la camara.
2. Detecta rostro localmente.
3. Genera embedding localmente.
4. Compara contra una cache local de empleados.
5. Reproduce voz: "Bienvenido Carlos".
6. Envia al backend solo un evento liviano.

## Instalacion local futura

```powershell
cd C:\SpringProjectsnew\ia_facial\edge
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main
```

Si estas en `cmd.exe`, no uses `Activate.ps1`. Usa:

```bat
cd C:\SpringProjectsnew\ia_facial\edge
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.main
```

Tambien puedes ejecutar:

```bat
scripts\setup_windows_cmd.bat
scripts\run_edge_cmd.bat
```

## Modelos

La carpeta `models/` queda reservada para modelos ONNX de deteccion y reconocimiento. No se suben modelos pesados al repositorio.

## Cache local

La carpeta `data/` guarda cache local del dispositivo:

- `employee_embeddings.json`
- cola offline de eventos pendientes
- configuracion de dispositivo
