$ErrorActionPreference = "Stop"

$Backend = Join-Path $PSScriptRoot "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Backend is not set up. Run .\setup-local.ps1 first."
}

Set-Location $Backend
& $Python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000