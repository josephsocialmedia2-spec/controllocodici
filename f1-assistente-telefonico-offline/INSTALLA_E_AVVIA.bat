@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Installazione F1 Assistente Telefonico Offline

echo ============================================================
echo       F1 ASSISTENTE TELEFONICO OFFLINE
echo ============================================================
echo.

set "PY_CMD="
py -3.12 -c "import sys" >nul 2>nul && set "PY_CMD=py -3.12"
if not defined PY_CMD py -3.11 -c "import sys" >nul 2>nul && set "PY_CMD=py -3.11"
if not defined PY_CMD py -3.10 -c "import sys" >nul 2>nul && set "PY_CMD=py -3.10"
if not defined PY_CMD py -3 -c "import sys" >nul 2>nul && set "PY_CMD=py -3"

if not defined PY_CMD (
    echo Python non e stato trovato.
    echo Installa Python 3.10, 3.11 o 3.12 a 64 bit e seleziona "Add Python to PATH".
    pause
    exit /b 1
)

%PY_CMD% -c "import struct,sys; assert struct.calcsize('P')*8 == 64, 'Serve Python 64 bit'; print(sys.version)"
if errorlevel 1 goto :errore

if not exist ".venv\Scripts\python.exe" (
    echo Creazione ambiente locale...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto :errore
)

".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :errore
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :errore
".venv\Scripts\python.exe" -m compileall -q app.py f1 tools
if errorlevel 1 goto :errore
".venv\Scripts\python.exe" "tools\download_model.py"
if errorlevel 1 goto :errore

echo Installazione completata.
start "F1 Assistente Telefonico" ".venv\Scripts\pythonw.exe" "%~dp0app.py"
exit /b 0

:errore
echo.
echo INSTALLAZIONE NON COMPLETATA.
pause
exit /b 1
