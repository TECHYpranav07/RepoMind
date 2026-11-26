# RepoMind PowerShell Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "             RepoMind Project Launcher" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Launching Backend (FastAPI) and Frontend (Vite)...`n" -ForegroundColor Yellow

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Launch Backend
$backendDir = Join-Path $rootDir "RepoMind"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$backendDir`" && venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload" -WindowStyle Normal

Start-Sleep -Seconds 2

# Launch Frontend
$frontendDir = Join-Path $rootDir "repomind-explorer"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$frontendDir`" && npm run dev" -WindowStyle Normal

Write-Host "Backend running at:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Frontend running at: http://localhost:5173" -ForegroundColor Green
Write-Host "`nServices started in separate terminal windows." -ForegroundColor White
