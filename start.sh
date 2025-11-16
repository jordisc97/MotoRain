#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Start the backend API in the background
echo "Starting backend API..."
cd backend
uvicorn app_mobile:app --host 0.0.0.0 --port 8001 &
cd ..

# Start the Telegram bot in the foreground
echo "Starting Telegram bot..."
python -m telegram_bot.bot
