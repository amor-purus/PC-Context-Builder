@echo off
setlocal
chcp 65001 >nul
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not exist "%PYTHON_EXE%" (
  if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python314\python.exe"
)
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python 3.14 x64 was not found at the standard installation paths.
  echo Please install Python 3.14 x64 using the default location.
  pause
  exit /b 1
)
"%PYTHON_EXE%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,14) and sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
  echo [ERROR] This tool requires CPython 3.14 x64. No scan was started.
  "%PYTHON_EXE%" --version
  pause
  exit /b 1
)
echo [INFO] Python 3.14 x64 detected. Starting PC Context Builder...
"%PYTHON_EXE%" "%~dp0main.py"
if errorlevel 1 (
  echo.
  echo [ERROR] PC Context Builder exited with an error.
  pause
)
endlocal
