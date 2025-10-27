#!/bin/bash

# MotoRain Telegram Bot Startup Script
# ====================================

echo "🚀 Starting MotoRain Telegram Bot..."
echo "===================================="

# Check if we're in the right directory
if [ ! -f "motorain_bot.py" ]; then
    echo "❌ Error: motorain_bot.py not found!"
    echo "Please run this script from the telegram-bot directory."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Creating .env file template..."
    echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
    echo "Please edit .env file and add your bot token!"
    exit 1
fi

# Check if bot token is set
if grep -q "your_bot_token_here" .env; then
    echo "❌ Error: Please set your bot token in .env file!"
    echo "Get your token from @BotFather on Telegram."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    exit 1
fi

# Check if requirements are installed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check if backend is running
echo "🔍 Checking if MotoRain backend is running..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "⚠️  Warning: MotoRain backend is not running!"
    echo "Please start the backend first:"
    echo "  cd ../backend"
    echo "  python app.py"
    echo ""
    echo "Continuing anyway..."
fi

echo "🤖 Starting Telegram bot..."
python motorain_bot.py
