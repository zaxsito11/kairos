@echo off
REM kairos_runner_full.bat — Inicia KAIROS completo con API
echo.
echo  ╔══════════════════════════════════════╗
echo  ║         K A I R O S                 ║
echo  ╚══════════════════════════════════════╝

cd /d "C:\Users\NICO PC\Documents\kairos"
call venv\Scripts\activate

REM Instalar FastAPI si no está
pip install fastapi uvicorn python-multipart -q

REM Terminal 1: Monitor
start "KAIROS Monitor" cmd /k "venv\Scripts\activate && python src/monitor.py"

timeout /t 2 /nobreak > nul

REM Terminal 2: Dashboard
start "KAIROS Dashboard" cmd /k "venv\Scripts\activate && streamlit run src/dashboard_main.py"

timeout /t 2 /nobreak > nul

REM Terminal 3: API
start "KAIROS API" cmd /k "venv\Scripts\activate && uvicorn api:app --host 0.0.0.0 --port 8000 --reload --app-dir src"

echo.
echo KAIROS arrancado:
echo   Dashboard: http://localhost:8501
echo   API:       http://localhost:8000
echo   Docs API:  http://localhost:8000/docs
