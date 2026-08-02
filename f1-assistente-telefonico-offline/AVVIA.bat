@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    call "%~dp0INSTALLA_E_AVVIA.bat"
    exit /b
)

if not exist "models\vosk-model-small-it-0.22\am\final.mdl" (
    ".venv\Scripts\python.exe" "%~dp0tools\download_model.py"
    if errorlevel 1 (
        pause
        exit /b 1
    )
)

start "F1 Assistente Telefonico" ".venv\Scripts\pythonw.exe" "%~dp0app.py"
