# Generar token Gmail OAuth (ejecutar en tu PC, carpeta backend)

$Backend = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Backend

Write-Host "Instalando dependencias OAuth..."
& .\.venv\Scripts\pip.exe install -r requirements-gmail-oauth.txt

if (-not (Test-Path "credentials.json")) {
    Write-Host "ERROR: Falta credentials.json en backend/"
    Write-Host "Descargalo de Google Cloud Console -> APIs -> Gmail -> OAuth Desktop"
    exit 1
}

Write-Host "Se abrira el navegador. Autoriza la cuenta Gmail que ENVIARA los tokens."
& .\.venv\Scripts\python.exe generar_token.py

if (Test-Path "token.json") {
    Write-Host ""
    Write-Host "OK token.json creado."
    Write-Host "Sube al VPS:"
    Write-Host "  scp token.json root@104.238.215.26:/root/ia_facial/backend/token.json"
    Write-Host "  ssh root@104.238.215.26 systemctl restart ia-facial"
} else {
    Write-Host "ERROR: no se genero token.json"
}
