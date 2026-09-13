# Developer script to spin up Lenny Growth Assistant locally
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Starting The Lenny Growth Assistant (Local Dev)   " -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Cyan

# Check if Docker is running
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker daemon is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Spin up containers
Write-Host "Launching containers with Docker Compose..." -ForegroundColor Yellow
docker compose up -d --build

Write-Host "Containers started! Checking health status..." -ForegroundColor Green
Start-Sleep -Seconds 5
docker compose ps

Write-Host "Application is available at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "FastAPI Docs available at:  http://localhost:8000/docs" -ForegroundColor Cyan
