@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Esegui prima INSTALLA_E_AVVIA.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "%~dp0app.py" --demo
