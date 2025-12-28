@echo off
rem Change to the directory where this script is located
cd /d "%~dp0"

rem Check if Python is installed and accessible
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not found or not in PATH. Please install Python or add it to your PATH.
    echo Download Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

rem Install/Update required libraries if necessary
echo Installing/Updating Python dependencies...
python -m pip install -r requirements.txt --upgrade
if %errorlevel% neq 0 (
    echo Failed to install Python dependencies. Please check your internet connection and try again.
    pause
    exit /b 1
)

rem Run the main application
echo Starting Real-Time Voice Translator...
python main.py

echo Application finished.
pause