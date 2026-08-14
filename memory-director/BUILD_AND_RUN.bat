@echo off
setlocal
title Memory Director - Build

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"

if not exist "%CSC%" (
  echo ERRORE: compilatore .NET Framework csc.exe non trovato.
  echo Windows deve avere .NET Framework 4.x installato.
  pause
  exit /b 1
)

echo [1/3] Compilo il test...
"%CSC%" /nologo /target:exe /optimize+ /out:"%~dp0MemoryDirector.Tests.exe" ^
  /reference:System.Windows.Forms.dll ^
  /reference:System.Drawing.dll ^
  /reference:System.Web.Extensions.dll ^
  /reference:System.Speech.dll ^
  "%~dp0MemoryDirector.cs"
if errorlevel 1 goto :fail

echo [2/3] Eseguo i self-test...
"%~dp0MemoryDirector.Tests.exe" --self-test
if errorlevel 1 goto :fail

echo [3/3] Compilo l'app Windows...
"%CSC%" /nologo /target:winexe /optimize+ /out:"%~dp0MemoryDirector.exe" ^
  /reference:System.Windows.Forms.dll ^
  /reference:System.Drawing.dll ^
  /reference:System.Web.Extensions.dll ^
  /reference:System.Speech.dll ^
  "%~dp0MemoryDirector.cs"
if errorlevel 1 goto :fail

del /q "%~dp0MemoryDirector.Tests.exe" 2>nul

echo.
echo BUILD E TEST: OK
echo Avvio Memory Director...
start "" "%~dp0MemoryDirector.exe"
exit /b 0

:fail
echo.
echo BUILD O TEST FALLITO. Memory Director NON viene avviato.
pause
exit /b 1
