@echo off
REM kairos_runner.bat — Inicia KAIROS en produccion
REM Doble clic para arrancar todo

echo.
echo  ╔══════════════════════════════════════╗
echo  ║         K A I R O S                 ║
echo  ║   Arrancando sistema completo...    ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "C:\Users\NICO PC\Documents\kairos"
call venv\Scripts\activate

REM Terminal 1: Monitor (en background)
echo [1] Iniciando monitor de alertas...
start "KAIROS Monitor" cmd /k "venv\Scripts\activate && python src/monitor.py"

REM Esperar 3 segundos
timeout /t 3 /nobreak > nul

REM Terminal 2: Dashboard
echo [2] Iniciando dashboard...
start "KAIROS Dashboard" cmd /k "venv\Scripts\activate && streamlit run src/dashboard_main.py"

echo.
echo KAIROS arrancado. Cierra las ventanas para detener.
