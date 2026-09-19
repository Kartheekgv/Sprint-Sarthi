$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python is required. Install Python 3.11 or newer, then run this script again."
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js is required. Install Node.js 20 or newer, then run this script again."
}

Write-Host "Creating the Python virtual environment..."
if (-not (Test-Path (Join-Path $Backend ".venv\Scripts\python.exe"))) {
    py -3 -m venv (Join-Path $Backend ".venv")
}

$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Alembic = Join-Path $Backend ".venv\Scripts\alembic.exe"
Write-Host "Installing backend dependencies..."
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Python package upgrade failed." }
& $Python -m pip install -e "$Backend[test]"
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }

if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Copy-Item (Join-Path $Backend ".env.example") (Join-Path $Backend ".env")
}

Write-Host "Applying database migrations..."
Push-Location $Backend
try {
    & $Alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
} finally {
    Pop-Location
}

Write-Host "Installing frontend dependencies..."
Push-Location $Frontend
try {
    npx --yes pnpm@10.34.5 install --frozen-lockfile
} finally {
    Pop-Location
}

Write-Host "Setup complete. Start the backend and frontend in separate PowerShell windows."