$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

$python311 = py -3.11 --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "No se encontro Python 3.11."
    Write-Host "Instala Python 3.11 para evitar problemas con DeepFace/TensorFlow en Windows."
    Write-Host "Luego vuelve a ejecutar este script."
    exit 1
}

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Listo. Ejecuta:"
Write-Host "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
