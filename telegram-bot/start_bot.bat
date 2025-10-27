@echo off
echo 🚀 Starting MotoRain Telegram Bot...
echo ====================================

REM Check if we're in the right directory
if not exist "motorain_bot.py" (
    echo ❌ Error: motorain_bot.py not found!
    echo Please run this script from the telegram-bot directory.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️  Warning: .env file not found!
    echo Creating .env file template...
    echo TELEGRAM_BOT_TOKEN=your_bot_token_here > .env
    echo Please edit .env file and add your bot token!
    pause
    exit /b 1
)

REM Check if bot token is set
findstr /C:"your_bot_token_here" .env >nul
if %errorlevel% == 0 (
    echo ❌ Error: Please set your bot token in .env file!
    echo Get your token from @BotFather on Telegram.
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed!
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if requirements are installed
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Check if backend is running
echo 🔍 Checking if MotoRain backend is running...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Warning: MotoRain backend is not running!
    echo Please start the backend first:
    echo   cd ..\backend
    echo   python app.py
    echo.
    echo Continuing anyway...
)

echo 🤖 Starting Telegram bot...
python motorain_bot.py

pause
