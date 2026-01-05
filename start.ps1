# RecoverAI Local Startup Script
Write-Host "Starting RecoverAI Ecosystem Locally..." -ForegroundColor Cyan

# 1. Start Backend in Background
Write-Host "Launching Backend API (Port 8000)..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "main:app --host 0.0.0.0 --port 8000 --reload" 
Write-Host "Backend Running."

# 2. Setup & Start Frontend
Write-Host "Setting up Frontend (Port 5173)..." -ForegroundColor Green
Set-Location "./frontend"

# Check if node_modules exists, if not install
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node Dependencies (First Run)..." -ForegroundColor Yellow
    npm install
}

Write-Host "Launching Frontend Dashboard..." -ForegroundColor Green
npm run dev

# Return to root
Set-Location ".."
