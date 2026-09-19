$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install it from https://docs.docker.com/desktop/ and run this script again."
}

docker compose version | Out-Null
docker info | Out-Null

Write-Host "Building and starting Sprint Sarthi..."
docker compose up --build --detach --remove-orphans

Write-Host "Waiting for services..."
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:3000/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
        Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5 | Out-Null
        break
    } catch {
        if ($attempt -eq 30) {
            docker compose ps
            docker compose logs --tail=80
            throw "Sprint Sarthi did not become ready."
        }
        Start-Sleep -Seconds 2
    }
}

Write-Host ""
Write-Host "Sprint Sarthi is running:"
Write-Host "  Frontend: http://localhost:3000"
Write-Host "  API:      http://localhost:3000/api/v1"
Write-Host "  Health:   http://localhost:3000/health"
Write-Host ""
Write-Host "View logs: docker compose logs -f"
Write-Host "Stop:      docker compose down"