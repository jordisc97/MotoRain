# MotoRain Telegram Bot - Deployment Guide

## 🚀 Overview

The MotoRain Telegram Bot provides the same weather analysis functionality as the mobile app, but accessible through Telegram. This makes it much easier to deploy and use - no App Store, no sideloading, just a simple bot that works on any device with Telegram.

## ✅ Benefits of Telegram Bot Approach

- **🌍 Universal Access**: Works on any device with Telegram (iOS, Android, Desktop, Web)
- **🚀 Easy Deployment**: No App Store approval or sideloading required
- **💰 Free**: No developer account fees or hosting costs
- **🔧 Simple Setup**: Just run a Python script
- **📱 Cross-Platform**: Same experience on all devices
- **🔄 Automatic Updates**: Update the bot without users needing to update apps

## 📋 Prerequisites

### Required Software
- **Python 3.8+**
- **Telegram Bot Token** (free from @BotFather)
- **MotoRain Backend** (for weather analysis)

### Required Accounts
- **Telegram Account** (free)
- **BotFather Access** (to create your bot)

## 🛠️ Step-by-Step Setup

### Step 1: Create Your Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a chat** with BotFather
3. **Send `/newbot`** command
4. **Follow the prompts**:
   - Bot name: `MotoRain Weather Bot`
   - Bot username: `yourname_motorain_bot` (must be unique)
5. **Save the bot token** - you'll need this!

### Step 2: Set Up the Bot Code

1. **Navigate to telegram-bot directory**:
   ```bash
   cd telegram-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   # Create .env file
   echo "TELEGRAM_BOT_TOKEN=your_bot_token_here" > .env
   ```

4. **Make sure MotoRain backend is running**:
   ```bash
   # In another terminal, start the backend
   cd ../backend
   python app.py
   ```

### Step 3: Configure the Bot

1. **Update config.env** with your settings:
   ```bash
   # Edit config.env
   BOT_NAME=Your MotoRain Bot
   BOT_USERNAME=your_bot_username
   WEATHER_API_URL=http://localhost:8000
   CHROMEDRIVER_PATH=../chromedriver/chromedriver.exe
   ```

2. **Set up ChromeDriver** (if not already done):
   ```bash
   # Make sure ChromeDriver is in the right location
   chmod +x ../chromedriver/chromedriver.exe
   ```

### Step 4: Run the Bot

1. **Start the bot**:
   ```bash
   python motorain_bot.py
   ```

2. **Test the bot**:
   - Open Telegram
   - Search for your bot username
   - Send `/start` command
   - Follow the setup process

## 🎯 Bot Features

### Core Commands
- `/start` - Welcome message and main menu
- `/weather` - Check weather for your commute route
- `/settings` - Configure your addresses and preferences
- `/help` - Show help and available commands

### Interactive Features
- **🏠 Address Setup**: Set home and work addresses
- **📅 Commute Days**: Configure which days you commute
- **⏰ Commute Times**: Set morning and evening commute times
- **🔔 Notifications**: Enable/disable automatic rain alerts
- **🌤️ Weather Maps**: View weather analysis with route maps

### Automated Features
- **🌧️ Rain Alerts**: Automatic notifications before commute times
- **☀️ Clear Weather**: Notifications when it's safe to cycle
- **📊 Route Analysis**: Detailed weather analysis along your route
- **💡 Recommendations**: Smart suggestions for transport method

## 🔧 Advanced Configuration

### Customizing Notifications

Edit the bot code to customize notification timing:

```python
# In motorain_bot.py, modify these settings:
MORNING_COMMUTE_BUFFER_MINUTES = 30  # Alert 30 min before morning commute
EVENING_COMMUTE_BUFFER_MINUTES = 30  # Alert 30 min before evening commute
CHECK_INTERVAL_MINUTES = 30          # Check weather every 30 minutes
```

### Adding New Commands

To add new commands, edit `motorain_bot.py`:

```python
async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newcommand"""
    await update.message.reply_text("New command response")

# Add to the run() method:
application.add_handler(CommandHandler("newcommand", self.new_command))
```

### Database Integration

For production use, consider replacing the JSON file with a proper database:

```python
# Example with SQLite
import sqlite3

def init_database():
    conn = sqlite3.connect('motorain_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            home_address TEXT,
            work_address TEXT,
            commute_days TEXT,
            morning_commute TEXT,
            evening_commute TEXT,
            notifications_enabled BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()
```

## 🚀 Deployment Options

### Option 1: Local Development
```bash
# Run locally for testing
python motorain_bot.py
```

### Option 2: VPS Deployment
```bash
# On your VPS
git clone https://github.com/yourusername/MotoRain.git
cd MotoRain/telegram-bot
pip install -r requirements.txt
nohup python motorain_bot.py &
```

### Option 3: Cloud Deployment

#### Heroku
```bash
# Create Procfile
echo "worker: python motorain_bot.py" > Procfile

# Deploy
git add .
git commit -m "Deploy Telegram bot"
git push heroku main
```

#### Railway
```bash
# Connect to Railway
railway login
railway init
railway up
```

#### DigitalOcean App Platform
```bash
# Create app.yaml
echo "name: motorain-telegram-bot
services:
- name: bot
  source_dir: telegram-bot
  run_command: python motorain_bot.py
  environment_slug: python
  instance_count: 1
  instance_size: basic-xxs" > app.yaml
```

## 🔐 Security Considerations

### Bot Token Security
- **Never commit** your bot token to version control
- **Use environment variables** for sensitive data
- **Rotate tokens** regularly if compromised

### User Data Protection
- **Minimal data collection**: Only store necessary user settings
- **Data encryption**: Consider encrypting sensitive user data
- **Regular backups**: Backup user settings regularly

### Rate Limiting
```python
# Implement rate limiting
from telegram.ext import MessageHandler, filters

# Add rate limiting decorator
def rate_limit(func):
    def wrapper(*args, **kwargs):
        # Implement rate limiting logic
        pass
    return wrapper
```

## 📊 Monitoring and Logging

### Logging Configuration
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('motorain_bot.log'),
        logging.StreamHandler()
    ]
)
```

### Health Checks
```python
async def health_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check command"""
    await update.message.reply_text("✅ Bot is running and healthy!")
```

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check if bot token is correct
   - Verify internet connection
   - Check bot logs for errors

2. **Weather analysis fails**:
   - Ensure MotoRain backend is running
   - Check ChromeDriver installation
   - Verify API endpoints

3. **Notifications not working**:
   - Check user notification settings
   - Verify commute times are set correctly
   - Check bot is running continuously

### Debug Commands
```bash
# Check bot status
python -c "import motorain_bot; print('Bot module loaded successfully')"

# Test weather API
curl http://localhost:8000/health

# Check ChromeDriver
../chromedriver/chromedriver.exe --version
```

## 📈 Scaling Considerations

### For Multiple Users
- **Database**: Use PostgreSQL or MySQL instead of JSON files
- **Caching**: Implement Redis for weather data caching
- **Load Balancing**: Use multiple bot instances
- **Monitoring**: Add comprehensive logging and monitoring

### Performance Optimization
```python
# Implement caching
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Cache weather data
def get_cached_weather(route_key):
    cached = redis_client.get(route_key)
    if cached:
        return json.loads(cached)
    return None
```

## 🎉 Success!

Once deployed, your MotoRain Telegram Bot will:

- ✅ **Provide weather analysis** for any user's commute route
- ✅ **Send automatic rain alerts** before commute times
- ✅ **Work on all devices** with Telegram installed
- ✅ **Scale easily** to handle multiple users
- ✅ **Update automatically** when you push code changes

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review bot logs for error messages
- Test individual components (backend, ChromeDriver, etc.)
- Create an issue on GitHub for bugs or feature requests

---

**Happy botting! 🤖 Your MotoRain Telegram Bot is ready to help users stay dry on their commute!**
