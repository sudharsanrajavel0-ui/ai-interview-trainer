@echo off
echo ========================================
echo   AI Interview Trainer
echo   Starting server on http://localhost:8000
echo ========================================
echo.
cd /d "%~dp0"
set PYTHON=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo ERROR: Python not found in venv. Run: python -m venv venv
    pause
    exit /b 1
)
"%PYTHON%" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
pause
