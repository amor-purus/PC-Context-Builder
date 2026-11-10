@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not exist "%PYTHON_EXE%" (
  if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python314\python.exe"
)
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python 3.14 x64 was not found at the standard installation paths.
  echo Please install Python 3.14 x64 using the default location.
  pause
  popd
  exit /b 1
)
"%PYTHON_EXE%" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,14) and sys.maxsize > 2**32 else 1)"
if errorlevel 1 (
  echo [ERROR] This tool requires CPython 3.14 x64. No scan was started.
  "%PYTHON_EXE%" --version
  pause
  popd
  exit /b 1
)
set "APP_NAME="
for /f "delims=" %%A in ('"%PYTHON_EXE%" -c "from app_config import APP_NAME; print(APP_NAME)"') do set "APP_NAME=%%A"
if not defined APP_NAME (
  echo [ERROR] Could not read the application name from app_config.py.
  popd
  pause
  exit /b 1
)
echo [INFO] Python 3.14 x64 detected. Starting %APP_NAME%...
"%PYTHON_EXE%" "%~dp0main.py"
if errorlevel 1 (
  echo.
  echo [ERROR] %APP_NAME% exited with an error.
  pause
)
popd
endlocal
