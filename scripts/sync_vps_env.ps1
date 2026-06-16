# Sincroniza .env y token.json al VPS. Ejecutar desde la raiz del repo.
$VpsHost = "104.238.215.26"
$User = "root"
$Backend = "C:\SpringProjectsnew\ia_facial\backend"

Write-Host "Subiendo .env y token.json a $User@${VpsHost}..."
scp "$Backend\.env" "${User}@${VpsHost}:/root/ia_facial/backend/.env"
if (Test-Path "$Backend\token.json") {
  scp "$Backend\token.json" "${User}@${VpsHost}:/root/ia_facial/backend/token.json"
  Write-Host "token.json subido."
} else {
  Write-Host "AVISO: No existe backend\token.json - ejecuta backend\setup_gmail_token.ps1 primero"
}
Write-Host "En el VPS: systemctl restart ia-facial"
