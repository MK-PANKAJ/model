@echo off
echo ===========================================
echo Starting RecoverAI System...
echo ===========================================

:: 1. Start Backend in a new window
echo Starting Backend (FastAPI)...
start "RecoverAI Backend" cmd /k "uvicorn main:app --reload --host 0.0.0.0"

:: 2. Start Frontend in a new window
echo Starting Frontend (React)...
cd frontend
start "RecoverAI Frontend" cmd /k "npm run dev"
cd ..

:: 3. Wait regarding for servers to boot
echo Waiting for servers to launch...
timeout /t 5 >nul

:: 4. Open Browser
echo Opening Portal...
start http://localhost:5173
start http://localhost:8000/docs

echo ===========================================
echo System is Running!
echo Frontend: http://localhost:5173
echo Backend API: http://localhost:8000/docs
echo Close the command windows to stop.
echo ===========================================
pause
