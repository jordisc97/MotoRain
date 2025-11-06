# MotoRain Deployment Guide

This guide explains how to deploy MotoRain to a Linux server.

## Prerequisites

- Linux server (Ubuntu/Debian recommended)
- Python 3.8 or higher
- Root/sudo access
- Chrome/Chromium installed (for web scraping)

## Quick Deployment

1. **Upload files to server:**
   ```bash
   scp -r backend telegram_bot deploy user@your-server:/tmp/motorain/
   ```

2. **SSH into server:**
   ```bash
   ssh user@your-server
   ```

3. **Run deployment script:**
   ```bash
   cd /tmp/motorain
   sudo chmod +x deploy/deploy.sh
   sudo ./deploy/deploy.sh
   ```

## Manual Deployment

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv chromium-browser chromium-chromedriver
```

### 2. Create Application Directory

```bash
sudo mkdir -p /opt/motorain
sudo mkdir -p /opt/motorain/backend
sudo mkdir -p /opt/motorain/telegram_bot
```

### 3. Copy Application Files

```bash
sudo cp -r backend/* /opt/motorain/backend/
sudo cp -r telegram_bot/* /opt/motorain/telegram_bot/
```

### 4. Create Virtual Environment

```bash
sudo python3 -m venv /opt/motorain/venv
sudo /opt/motorain/venv/bin/pip install --upgrade pip
```

### 5. Install Python Dependencies

```bash
sudo /opt/motorain/venv/bin/pip install -r /opt/motorain/backend/requirements.txt
sudo /opt/motorain/venv/bin/pip install -r /opt/motorain/telegram_bot/requirements.txt
```

### 6. Configure Environment Variables

Edit `/opt/motorain/telegram_bot/bot.py` and update:
- `TELEGRAM_TOKEN`: Your Telegram bot token
- `BACKEND_API_URL`: Backend URL (use server IP or domain)

### 7. Install Systemd Services

```bash
sudo cp deploy/systemd/motorain-backend.service /etc/systemd/system/
sudo cp deploy/systemd/motorain-telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 8. Start Services

```bash
sudo systemctl enable motorain-backend
sudo systemctl enable motorain-telegram-bot
sudo systemctl start motorain-backend
sudo systemctl start motorain-telegram-bot
```

## Service Management

### View Logs

```bash
# Backend logs
journalctl -u motorain-backend -f

# Bot logs
journalctl -u motorain-telegram-bot -f
```

### Restart Services

```bash
sudo systemctl restart motorain-backend
sudo systemctl restart motorain-telegram-bot
```

### Stop Services

```bash
sudo systemctl stop motorain-backend
sudo systemctl stop motorain-telegram-bot
```

### Check Status

```bash
sudo systemctl status motorain-backend
sudo systemctl status motorain-telegram-bot
```

## Updating the Application

1. **Stop services:**
   ```bash
   sudo systemctl stop motorain-backend motorain-telegram-bot
   ```

2. **Update files:**
   ```bash
   sudo cp -r backend/* /opt/motorain/backend/
   sudo cp -r telegram_bot/* /opt/motorain/telegram_bot/
   ```

3. **Update dependencies (if needed):**
   ```bash
   sudo /opt/motorain/venv/bin/pip install -r /opt/motorain/backend/requirements.txt
   sudo /opt/motorain/venv/bin/pip install -r /opt/motorain/telegram_bot/requirements.txt
   ```

4. **Start services:**
   ```bash
   sudo systemctl start motorain-backend
   sudo systemctl start motorain-telegram-bot
   ```

## Troubleshooting

### Backend not starting

- Check logs: `journalctl -u motorain-backend -n 50`
- Verify port 8000 is not in use: `sudo netstat -tulpn | grep 8000`
- Check Python path in service file

### Bot not responding

- Check logs: `journalctl -u motorain-telegram-bot -n 50`
- Verify backend is running: `curl http://localhost:8000/health`
- Check Telegram token is correct

### ChromeDriver issues

- Install Chrome/Chromium: `sudo apt install chromium-browser`
- The app uses webdriver-manager to auto-download ChromeDriver

## Security Notes

- The services run as `www-data` user (limited permissions)
- Backend listens on all interfaces (0.0.0.0) - consider firewall rules
- Use HTTPS in production (nginx reverse proxy recommended)

