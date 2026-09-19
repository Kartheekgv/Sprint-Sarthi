$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install it from https://docs.docker.com/desktop/ and run this script again."
}

docker compose version | Out-Null
docker info | Out-Null

Write-Host "Building and starting Sprint Sarthi..."
docker compose up --build --detach --remove-orphans

Write-Host ""
Write-Host "Sprint Sarthi is running:"
Write-Host "  Frontend: http://localhost:3000"
Write-Host "  API:      http://localhost:8000"
Write-Host "  Health:   http://localhost:8000/health"
Write-Host ""
Write-Host "View logs: docker compose logs -f"
Write-Host "Stop:      docker compose down"