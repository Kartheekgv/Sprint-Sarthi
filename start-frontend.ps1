$ErrorActionPreference = "Stop"

$Frontend = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    throw "Frontend is not set up. Run .\setup-local.ps1 first."
}

Set-Location $Frontend
$env:BACKEND_INTERNAL_URL = "http://127.0.0.1:8000"
npx --yes pnpm@10.34.5 dev