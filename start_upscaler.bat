@echo off
setlocal
title AI Upscaler Launcher

:: Get the directory where this batch file is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo 🔎 Detecting environment...

:: Check for common virtual environment folders (venv or .venv)
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo Using virtual environment: venv
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo Using virtual environment: .venv
) else (
    set "PYTHON_EXE=python"
    echo No venv found, using system Python.
)

echo.
echo 🚀 Starting Discord Bot Interface...
:: Using %PYTHON_EXE% ensures both windows use the same environment
start "Discord Bot" cmd /k "%PYTHON_EXE% bot.py"

echo 👷 Starting AI Processing Worker...
start "AI Worker" cmd /k "%PYTHON_EXE% worker.py"

echo.
echo ✅ Both processes are running from: %PROJECT_DIR%
echo 💡 Close the individual windows to stop the services.
pause