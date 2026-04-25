@echo off
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found.
    echo Please run install.bat first.
    call .\install.bat
    pause
)

call venv\Scripts\activate.bat

@REM echo Checking dependencies...
@REM pip install -r requirements.txt -q

echo Starting application...
python main.py

