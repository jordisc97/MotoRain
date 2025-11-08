"""
Simple script to test if the Telegram bot can connect to Telegram API.
Run this before starting the main bot to verify the token is correct.
"""
import logging
from telegram import Bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token
TELEGRAM_TOKEN = "8477567862:AAH2l1W3WztMZI5cbSY5W0oK0r4X7kRZKcg"


async def test_connection():
    """Test if we can connect to Telegram API."""
    try:
        logger.info("Testing Telegram bot connection...")
        bot = Bot(token=TELEGRAM_TOKEN)
        
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Successfully connected to Telegram!")
        logger.info(f"Bot username: @{bot_info.username}")
        logger.info(f"Bot name: {bot_info.first_name}")
        logger.info(f"Bot ID: {bot_info.id}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to Telegram: {str(e)}")
        logger.error("Please check:")
        logger.error("1. Is the Telegram token correct?")
        logger.error("2. Is python-telegram-bot installed? (pip install python-telegram-bot)")
        logger.error("3. Are there any network/firewall issues?")
        return False


if __name__ == '__main__':
    import asyncio
    success = asyncio.run(test_connection())
    if success:
        print("\n[SUCCESS] Bot connection test passed! You can now run bot.py")
    else:
        print("\n[ERROR] Bot connection test failed! Please fix the issues above.")
        exit(1)

