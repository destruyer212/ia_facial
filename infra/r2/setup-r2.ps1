$ErrorActionPreference = "Stop"

if (-not $env:R2_ACCOUNT_ID) { throw "Falta R2_ACCOUNT_ID" }
if (-not $env:R2_ACCESS_KEY_ID) { throw "Falta R2_ACCESS_KEY_ID" }
if (-not $env:R2_SECRET_ACCESS_KEY) { throw "Falta R2_SECRET_ACCESS_KEY" }
if (-not $env:R2_BUCKET) { throw "Falta R2_BUCKET" }

$endpoint = if ($env:R2_ENDPOINT) { $env:R2_ENDPOINT } else { "https://$($env:R2_ACCOUNT_ID).r2.cloudflarestorage.com" }
$corsFile = Join-Path $PSScriptRoot "cors.json"

Write-Host "Creando bucket $($env:R2_BUCKET) (si no existe)..."
aws s3api create-bucket `
  --bucket $env:R2_BUCKET `
  --endpoint-url $endpoint 2>$null

Write-Host "Aplicando CORS..."
aws s3api put-bucket-cors `
  --bucket $env:R2_BUCKET `
  --cors-configuration file://$corsFile `
  --endpoint-url $endpoint

Write-Host "R2 listo."
