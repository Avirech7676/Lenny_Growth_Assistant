# One-Command Launch Script for The Lenny Growth Assistant
param (
    [string]$Mode = "Docker" # Options: 'Docker' or 'BareMetal'
)

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  The Lenny Growth Assistant — Startup Launcher      " -ForegroundColor Green
Write-Host "  Mode: $Mode                                       " -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Cyan

if ($Mode -eq "Docker") {
    # Check if Docker is running
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker daemon not detected. Falling back to BareMetal mode..." -ForegroundColor Yellow
        $Mode = "BareMetal"
    } else {
        Write-Host "Launching multi-container stack via Docker Compose..." -ForegroundColor Yellow
        docker compose up -d --build
        Write-Host "Waiting for service health checks..." -ForegroundColor Green
        Start-Sleep -Seconds 6
        docker compose ps
        Write-Host ""
        Write-Host "🚀 Growth Canvas Frontend: http://localhost:3000" -ForegroundColor Green
        Write-Host "📚 FastAPI Backend & Docs: http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host "📊 Database Engine:       PostgreSQL 16 + pgvector (:5432)" -ForegroundColor White
        exit 0
    }
}

if ($Mode -eq "BareMetal") {
    Write-Host "Starting Bare-Metal Local Development Runtimes..." -ForegroundColor Cyan
    
    # 1. Set PYTHONPATH
    $env:PYTHONPATH = ".;backend"
    
    # 2. Ingest transcripts if needed
    Write-Host "Checking transcript embeddings cache..." -ForegroundColor Yellow
    python -m ingestion.ingest
    
    Write-Host "Starting FastAPI backend on :8000..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; `$env:PYTHONPATH='.;backend'; python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload"
    
    Write-Host "Starting Vite frontend dev server on :3000..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\frontend'; npm run dev"
    
    Start-Sleep -Seconds 4
    Write-Host ""
    Write-Host "🚀 Growth Canvas Frontend: http://localhost:3000" -ForegroundColor Green
    Write-Host "📚 FastAPI Backend & Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
    Write-Host "💾 Database Engine:       SQLite Fallback (bare-metal mode)" -ForegroundColor White
}
