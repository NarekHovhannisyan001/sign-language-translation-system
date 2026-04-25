@echo off
echo ============================================
echo   Installing SLTS - Sign Language Translator
echo ============================================
echo.

where py >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python Launcher not found. Install Python 3.9 from python.org
    pause
    exit /b 1
)

echo Creating virtual environment with Python 3.9...
py -3.9 -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Python 3.9 not found. Install it from python.org
    pause
    exit /b 1
)

echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ============================================
echo   Installation complete!
echo   Double-click START_SLTS.bat to run.
echo ============================================