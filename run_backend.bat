@echo off
cd /d "%~dp0RepoMind"
echo Starting RepoMind FastAPI Backend on http://127.0.0.1:8000 ...
venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
pause
