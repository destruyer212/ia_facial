# Setup Windows

## Version de Python

En este equipo se detecto Python 3.13 con:

```powershell
py -0p
```

Para este MVP recomiendo instalar Python 3.11, porque el stack DeepFace/TensorFlow suele ser mas estable ahi con las versiones fijadas en `requirements.txt`.

Referencia oficial de instalacion TensorFlow: https://www.tensorflow.org/install/pip

## Pasos

```powershell
cd C:\SpringProjectsnew\ia_facial\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Si usas celular fisico

Ejecuta:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Y desde Flutter usa:

```text
http://IP_DE_TU_PC:8000
```

## Si usas emulador Android

Usa:

```text
http://10.0.2.2:8000
```
