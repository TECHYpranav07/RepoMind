@echo off
title RepoMind Launcher
echo ========================================================
echo               RepoMind Project Launcher
echo ========================================================
echo Starting RepoMind FastAPI Backend and React Frontend...
echo.

cd /d "%~dp0"

:: Start Backend in a new window
start "RepoMind Backend (FastAPI :8000)" cmd /k "cd /d "%~dp0RepoMind" && venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload"

:: Wait 2 seconds for backend to initialize
timeout /t 2 /nobreak >nul

:: Start Frontend in a new window
start "RepoMind Frontend (Vite :5173)" cmd /k "cd /d "%~dp0repomind-explorer" && npm run dev"

echo Backend started at:  http://127.0.0.1:8000
echo Frontend started at: http://localhost:5173
echo.
echo Both services are running in separate windows.
echo Press any key to exit this launcher window...
pause >nul
