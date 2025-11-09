# 🌧️ MotoRain Telegram Bot

A Telegram bot that helps you check if it will rain during your commute, just like the mobile app!

## Features

- ✅ Interactive conversation to collect user information
- ✅ Real-time radar image generation
- ✅ Rain prediction for your commute route
- ✅ Beautiful formatted results with radar map

## Prerequisites

1. **Backend API must be running** on `http://localhost:8000`
   - The bot connects to the backend API to get rain predictions
   - Make sure the backend server is started before running the bot

2. **Python 3.8+** with required packages installed

## Installation

1. **Install dependencies:**
   ```bash
   cd telegram_bot
   pip install -r requirements.txt
   ```

2. **Verify the Telegram token** in `bot.py`:
   ```python
   TELEGRAM_TOKEN = "its_secret"
   ```

3. **Verify the backend API URL** in `bot.py`:
   ```python
   BACKEND_API_URL = "http://localhost:8000/check_rain/"
   ```
   (Adjust if your backend runs on a different port or host)

## Running the Bot

### Option 1: Direct Python execution

1. **Start the backend server first:**
   ```bash
   cd ../backend
   python -m uvicorn app_mobile:app --host 127.0.0.1 --port 8000
   ```

2. **In a new terminal, start the Telegram bot:**
   ```bash
   cd telegram_bot
   python bot.py
   ```

### Option 2: Using the startup script (Windows)

1. **Start the backend server:**
   ```bash
   scripts\start-backend.bat
   ```

2. **Start the Telegram bot:**
   ```bash
   telegram_bot\start.bat
   ```

## Usage

1. **Find your bot on Telegram:**
   - Search for your bot using the bot's username (from BotFather)
   - Or use the direct link: `https://t.me/your_bot_username`

2. **Start a conversation:**
   - Send `/start` to begin
   - Follow the prompts to provide:
     - Your name
     - Home address
     - Work address
     - Vehicle type (bike or motorbike)

3. **Get results:**
   - The bot will process your request
   - You'll receive a radar map image with your route
   - The bot will tell you if it will rain during your commute

## Commands

- `/start` - Start a new rain check
- `/cancel` - Cancel the current operation
- `/help` - Show help message
- `/test` - Test if bot is responding

## How It Works

1. **User provides information:**
   - The bot uses a conversation handler to collect user data step by step

2. **Bot calls backend API:**
   - Sends a POST request to `http://localhost:8000/check_rain/`
   - Includes user name, home address, work address, and vehicle type

3. **Backend processes request:**
   - Converts addresses to GPS coordinates
   - Analyzes radar data for the route
   - Generates an annotated map image

4. **Bot sends results:**
   - Decodes the base64 image from the API response
   - Sends the radar map image to the user
   - Displays rain prediction and route information

## Configuration

### Backend API URL

If your backend runs on a different host or port, update `BACKEND_API_URL` in `bot.py`:

```python
BACKEND_API_URL = "http://your-host:your-port/check_rain/"
```

### Telegram Token

The bot token is already configured in the code. If you need to change it:

```python
TELEGRAM_TOKEN = "your-telegram-bot-token"
```

## Troubleshooting

### Bot doesn't respond to /start

**Step 1: Test the bot connection**
```bash
cd telegram_bot
python test_connection.py
```

This will verify:
- The Telegram token is valid
- The bot can connect to Telegram API
- python-telegram-bot is installed correctly

**Step 2: Check if the bot is running**
- Look for "Starting MotoRain Telegram Bot..." in the console
- Look for "Bot is now running. Press Ctrl+C to stop."
- If you see errors, check the error messages

**Step 3: Test with /test command**
- Try sending `/test` to the bot
- If `/test` works but `/start` doesn't, there's an issue with the conversation handler
- If neither works, the bot might not be receiving messages

**Step 4: Verify the bot token**
- Make sure the token in `bot.py` matches your bot token from BotFather
- The token should look like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

**Step 5: Check for errors in console**
- Look for any error messages when starting the bot
- Common errors:
  - "Invalid token" - Token is wrong
  - "Connection error" - Network/firewall issue
  - "Module not found" - Missing dependencies

**Step 6: Verify dependencies**
```bash
pip install python-telegram-bot
pip install requests
```

**Step 7: Try restarting the bot**
- Stop the bot (Ctrl+C)
- Wait a few seconds
- Start it again: `python bot.py`

### Bot doesn't respond

- Check that the bot is running (look for "Starting MotoRain Telegram Bot..." in the console)
- Verify the Telegram token is correct
- Make sure you're messaging the correct bot
- Try the `/test` command first to verify basic functionality

### "Failed to connect to backend API"

- Ensure the backend server is running on `http://localhost:8000`
- Check that the backend API is accessible
- Verify the `BACKEND_API_URL` in `bot.py` is correct

### "Radar data not available yet"

- The backend needs time to scrape radar data on startup
- Wait a few moments and try again
- Check the backend server logs for errors

### Image not displaying

- Check that the backend successfully generated the map image
- Verify the image data is being properly decoded
- Check Telegram's file size limits (max 10MB for photos)

## Error Handling

The bot handles various error scenarios:

- **Backend API unavailable:** Shows error message to user
- **Invalid addresses:** Backend will return an error (handled by API)
- **Radar data not ready:** Backend returns 503 (handled by API)
- **User cancels:** Conversation is cancelled and data is cleaned up

## Notes

- The bot stores user data temporarily in memory (only during the conversation)
- User data is automatically cleaned up after the request completes
- Multiple users can use the bot simultaneously
- The bot uses the same backend API as the mobile app

## Support

For issues or questions:
- Check the backend server logs
- Check the bot console output
- Review the main README.md for backend setup instructions

