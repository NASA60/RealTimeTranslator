@echo off
cd /d "%~dp0"

echo Cleaning up previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

echo Installing dependencies...
python -m pip install pyinstaller requests tqdm

echo.
echo ========================================================
echo Step 1: Downloading Small Model for Bundling...
echo ========================================================
python prepare_build.py
if %errorlevel% neq 0 (
    echo Failed to prepare model.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo Step 2: Building Executable (GUI Mode)...
echo ========================================================
rem --noconsole: مخفی کردن صفحه سیاه CMD
rem --collect-all vosk: اضافه کردن کتابخانه های ضروری
rem --add-data: اضافه کردن مدل کوچک داخل فایل
pyinstaller --noconsole --onefile --name "VoiceTranslator" --add-data "bundled_model;bundled_model" --collect-all vosk main.py

echo.
echo ========================================================
echo Build Complete!
echo Your executable is in the "dist" folder.
echo It is now a full GUI application (no black window).
echo ========================================================
pause