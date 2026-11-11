@echo off
setlocal EnableExtensions
title FlClash Log Collector
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo FlClash Log Collector
echo ============================================================
echo.
echo Checking Python environment...

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 set "PY_CMD=python"
  )
)

if not defined PY_CMD (
  echo [ERROR] Python was not found.
  echo Install Python 3.10 or later from https://www.python.org/downloads/windows/
  echo Enable "Add Python to PATH" during installation.
  goto :END_ERROR
)

echo Checking Python version...
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo [ERROR] Python 3.10 or later is required.
  goto :END_ERROR
)

echo Checking websocket-client...
%PY_CMD% -c "import websocket" >nul 2>nul
if errorlevel 1 (
  echo Installing dependency...
  %PY_CMD% -m pip install --user -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check network access.
    goto :END_ERROR
  )
)

echo.
echo Starting collector. This window will remain open while it runs.
echo Startup diagnostics are written to collector-startup.log.
echo.
%PY_CMD% collector.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo [ERROR] Collector exited with code %EXIT_CODE%.
  echo See collector-startup.log for details.
) else (
  echo Collector stopped.
)
goto :END

:END_ERROR
echo.
echo Startup did not complete. Review the message above.

:END
echo.
echo Press any key to close this window...
pause >nul
endlocal