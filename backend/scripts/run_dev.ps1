$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..
.\.venv\Scripts\Activate.ps1
$env:PYTHONUNBUFFERED = "1"
# Sin --reload: evita ERR_NETWORK_CHANGED en registros largos (IA 1-3 min).
# Para desarrollo con autoreload: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
uvicorn app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 300
