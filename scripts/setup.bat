@echo off
echo MotoRain Setup Script
echo ====================
echo.
echo This script will help you set up the MotoRain application
echo.

echo Step 1: Creating Python virtual environment...
cd backend
python -m venv venv
echo Virtual environment created!

echo.
echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated!

echo.
echo Step 3: Installing Python dependencies...
pip install -r requirements.txt
echo Dependencies installed!

echo.
echo Step 4: Setup complete!
echo.
echo Next steps:
echo 1. Update ChromeDriver path in backend/app.py
echo 2. Run scripts/start-all.bat to start the application
echo.
echo ChromeDriver path should be updated to:
echo CHROMEDRIVER_PATH = r"..\chromedriver\chromedriver.exe"
echo.
pause
