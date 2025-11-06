#!/bin/bash

# MotoRain Deployment Script
# This script sets up the MotoRain application on a Linux server

set -e

echo "🚀 Starting MotoRain Deployment..."

# Configuration
APP_DIR="/opt/motorain"
VENV_DIR="$APP_DIR/venv"
USER="www-data"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Create application directory
echo "📁 Creating application directory..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/backend
mkdir -p $APP_DIR/telegram_bot
mkdir -p $APP_DIR/logs

# Copy application files
echo "📋 Copying application files..."
cp -r backend/* $APP_DIR/backend/
cp -r telegram_bot/* $APP_DIR/telegram_bot/

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source $VENV_DIR/bin/activate

# Install backend dependencies
pip install --upgrade pip
pip install -r $APP_DIR/backend/requirements.txt

# Install telegram bot dependencies
pip install -r $APP_DIR/telegram_bot/requirements.txt

# Set permissions
echo "🔐 Setting permissions..."
chown -R $USER:$USER $APP_DIR
chmod +x $APP_DIR/telegram_bot/bot.py

# Install systemd services
echo "⚙️ Installing systemd services..."
cp deploy/systemd/motorain-backend.service /etc/systemd/system/
cp deploy/systemd/motorain-telegram-bot.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable services
echo "✅ Enabling services..."
systemctl enable motorain-backend.service
systemctl enable motorain-telegram-bot.service

# Start services
echo "🚀 Starting services..."
systemctl start motorain-backend.service
sleep 5
systemctl start motorain-telegram-bot.service

# Show status
echo ""
echo "📊 Service Status:"
systemctl status motorain-backend.service --no-pager -l
echo ""
systemctl status motorain-telegram-bot.service --no-pager -l

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Useful commands:"
echo "  - View backend logs: journalctl -u motorain-backend -f"
echo "  - View bot logs: journalctl -u motorain-telegram-bot -f"
echo "  - Restart backend: systemctl restart motorain-backend"
echo "  - Restart bot: systemctl restart motorain-telegram-bot"
echo "  - Stop services: systemctl stop motorain-backend motorain-telegram-bot"

