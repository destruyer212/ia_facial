@echo off
setlocal

cd /d "%~dp0\.."

py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python 3.11.
  echo Instala Python 3.11 y vuelve a ejecutar este script.
  exit /b 1
)

py -3.11 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Listo. Ejecuta:
echo ".venv\Scripts\python.exe" -m app.main

