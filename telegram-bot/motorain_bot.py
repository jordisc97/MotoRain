#!/usr/bin/env python3
"""
MotoRain Telegram Bot
=====================

A Telegram bot that provides weather analysis for your commute route.
Same functionality as the mobile app, but accessible through Telegram.

Features:
- Real-time weather analysis
- Commute route checking
- Automated rain alerts
- User settings management
- Weather maps and recommendations
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Import the existing weather analysis logic
import sys
sys.path.append('../backend')
from radar_rain_checker import RadarRainChecker

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MotoRainTelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.radar_checker = RadarRainChecker()
        self.user_settings_file = 'user_settings.json'
        self.user_settings = self.load_user_settings()
        
    def load_user_settings(self) -> Dict:
        """Load user settings from file"""
        try:
            if os.path.exists(self.user_settings_file):
                with open(self.user_settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
        return {}
    
    async def save_user_settings(self):
        """Save user settings to file"""
        try:
            async with aiofiles.open(self.user_settings_file, 'w') as f:
                await f.write(json.dumps(self.user_settings, indent=2))
        except Exception as e:
            logger.error(f"Error saving user settings: {e}")
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Get settings for a specific user"""
        return self.user_settings.get(str(user_id), {
            'home_address': '',
            'work_address': '',
            'commute_days': {
                'monday': True, 'tuesday': True, 'wednesday': True,
                'thursday': True, 'friday': True, 'saturday': False, 'sunday': False
            },
            'morning_commute': {'enabled': True, 'time': '8:00'},
            'evening_commute': {'enabled': True, 'time': '17:30'},
            'notifications_enabled': True
        })
    
    async def set_user_setting(self, user_id: int, key: str, value):
        """Set a specific setting for a user"""
        if str(user_id) not in self.user_settings:
            self.user_settings[str(user_id)] = self.get_user_settings(user_id)
        
        self.user_settings[str(user_id)][key] = value
        await self.save_user_settings()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_text = f"""
🌧️ **Welcome to MotoRain Bot!** 🌧️

Hi {user.first_name}! I'm your personal weather assistant for your daily commute.

**What I can do:**
• 🌤️ Check weather conditions for your route
• 🚴‍♂️ Analyze rain patterns along your commute
• 📍 Remember your home and work addresses
• ⏰ Send you rain alerts before you leave
• 🗺️ Show you weather maps and recommendations

**Quick Commands:**
/weather - Check current weather for your route
/settings - Configure your addresses and preferences
/help - See all available commands

Let's get started! First, set your home and work addresses with /settings
        """
        
        keyboard = [
            [InlineKeyboardButton("🌤️ Check Weather", callback_data="check_weather")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weather command"""
        user_id = update.effective_user.id
        settings = self.get_user_settings(user_id)
        
        if not settings['home_address'] or not settings['work_address']:
            await update.message.reply_text(
                "❌ **Addresses not set!**\n\n"
                "Please set your home and work addresses first using /settings",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text("🌤️ **Checking weather for your route...**", parse_mode='Markdown')
        
        try:
            # Use the existing weather analysis logic
            result = await self.check_weather_for_route(
                settings['home_address'], 
                settings['work_address']
            )
            
            if result['success']:
                weather_text = f"""
🌧️ **Weather Analysis Complete!**

📍 **Route**: {settings['home_address']} → {settings['work_address']}

🌤️ **Current Conditions**: {result['weather_condition']}
☔ **Will it rain?**: {'Yes' if result['will_rain'] else 'No'}

💡 **Recommendation**: {result['recommendation']}

🕐 **Last updated**: {datetime.now().strftime('%H:%M')}
                """
                
                if result.get('image_b64'):
                    # Send weather map image
                    import base64
                    from io import BytesIO
                    
                    image_data = base64.b64decode(result['image_b64'])
                    await update.message.reply_photo(
                        photo=BytesIO(image_data),
                        caption=weather_text,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(weather_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(
                    f"❌ **Error checking weather**: {result.get('error', 'Unknown error')}",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Weather check error: {e}")
            await update.message.reply_text(
                "❌ **Sorry, I couldn't check the weather right now.**\n\n"
                "Please try again later or check your internet connection.",
                parse_mode='Markdown'
            )
    
    async def check_weather_for_route(self, home_address: str, work_address: str) -> Dict:
        """Check weather for a specific route"""
        try:
            # Use the existing radar rain checker
            result = self.radar_checker.check_rain_conditions(
                user="Telegram User",
                home=home_address,
                work=work_address,
                vehicle="bike"
            )
            
            return {
                'success': True,
                'will_rain': result.get('will_rain', False),
                'weather_condition': result.get('weather_condition', 'Unknown'),
                'recommendation': self.get_recommendation(result.get('will_rain', False)),
                'image_b64': result.get('image_b64')
            }
        except Exception as e:
            logger.error(f"Weather check error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_recommendation(self, will_rain: bool) -> str:
        """Get recommendation based on weather"""
        if will_rain:
            return "🌧️ **Consider taking public transport or driving today.** Rain is expected along your route."
        else:
            return "☀️ **Perfect weather for cycling!** No rain expected on your route."
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user_id = update.effective_user.id
        settings = self.get_user_settings(user_id)
        
        settings_text = f"""
⚙️ **Your Settings**

🏠 **Home Address**: {settings['home_address'] or 'Not set'}
🏢 **Work Address**: {settings['work_address'] or 'Not set'}

📅 **Commute Days**: {', '.join([day.capitalize() for day, enabled in settings['commute_days'].items() if enabled])}

🌅 **Morning Commute**: {'✅' if settings['morning_commute']['enabled'] else '❌'} {settings['morning_commute']['time']}
🌆 **Evening Commute**: {'✅' if settings['evening_commute']['enabled'] else '❌'} {settings['evening_commute']['time']}

🔔 **Notifications**: {'✅ Enabled' if settings['notifications_enabled'] else '❌ Disabled'}
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 Set Home Address", callback_data="set_home")],
            [InlineKeyboardButton("🏢 Set Work Address", callback_data="set_work")],
            [InlineKeyboardButton("📅 Commute Days", callback_data="commute_days")],
            [InlineKeyboardButton("⏰ Commute Times", callback_data="commute_times")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="notifications")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "check_weather":
            await self.weather_command(update, context)
        elif query.data == "settings":
            await self.settings_command(update, context)
        elif query.data == "help":
            await self.help_command(update, context)
        elif query.data == "main_menu":
            await self.start_command(update, context)
        elif query.data == "set_home":
            await query.edit_message_text(
                "🏠 **Set Home Address**\n\n"
                "Please send me your home address. I'll use this as the starting point for your commute analysis.\n\n"
                "Example: '123 Main Street, Barcelona, Spain'",
                parse_mode='Markdown'
            )
            context.user_data['waiting_for'] = 'home_address'
        elif query.data == "set_work":
            await query.edit_message_text(
                "🏢 **Set Work Address**\n\n"
                "Please send me your work address. I'll use this as the destination for your commute analysis.\n\n"
                "Example: '456 Business Avenue, Barcelona, Spain'",
                parse_mode='Markdown'
            )
            context.user_data['waiting_for'] = 'work_address'
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if 'waiting_for' in context.user_data:
            user_id = update.effective_user.id
            waiting_for = context.user_data['waiting_for']
            text = update.message.text
            
            if waiting_for == 'home_address':
                await self.set_user_setting(user_id, 'home_address', text)
                await update.message.reply_text(
                    f"✅ **Home address set!**\n\n"
                    f"📍 {text}\n\n"
                    f"Now set your work address to complete the setup.",
                    parse_mode='Markdown'
                )
                context.user_data['waiting_for'] = 'work_address'
                
            elif waiting_for == 'work_address':
                await self.set_user_setting(user_id, 'work_address', text)
                await update.message.reply_text(
                    f"✅ **Work address set!**\n\n"
                    f"📍 {text}\n\n"
                    f"🎉 **Setup complete!** You can now use /weather to check your commute conditions.",
                    parse_mode='Markdown'
                )
                del context.user_data['waiting_for']
        else:
            await update.message.reply_text(
                "🤔 I didn't understand that. Use /help to see available commands.",
                parse_mode='Markdown'
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
❓ **MotoRain Bot Commands**

**Main Commands:**
/start - Welcome message and main menu
/weather - Check weather for your commute route
/settings - Configure your addresses and preferences
/help - Show this help message

**What I do:**
🌤️ Analyze weather conditions along your commute route
🚴‍♂️ Provide recommendations for cycling vs. other transport
📍 Remember your home and work addresses
⏰ Send rain alerts before your commute times
🗺️ Show weather maps and route analysis

**Getting Started:**
1. Use /settings to set your home and work addresses
2. Use /weather to check current conditions
3. Enable notifications for automatic rain alerts

**Need help?** Just ask! I'm here to help you stay dry on your commute.
        """
        
        keyboard = [
            [InlineKeyboardButton("🌤️ Check Weather", callback_data="check_weather")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def daily_weather_check(self, context: ContextTypes.DEFAULT_TYPE):
        """Daily weather check for all users with notifications enabled"""
        logger.info("Running daily weather check...")
        
        for user_id_str, settings in self.user_settings.items():
            if not settings.get('notifications_enabled', False):
                continue
                
            user_id = int(user_id_str)
            
            # Check if it's a commute day
            today = datetime.now().strftime('%A').lower()
            if not settings['commute_days'].get(today, False):
                continue
            
            # Check if it's commute time (morning or evening)
            current_time = datetime.now().time()
            morning_time = datetime.strptime(settings['morning_commute']['time'], '%H:%M').time()
            evening_time = datetime.strptime(settings['evening_commute']['time'], '%H:%M').time()
            
            is_morning_commute = (
                settings['morning_commute']['enabled'] and
                abs((current_time.hour * 60 + current_time.minute) - 
                    (morning_time.hour * 60 + morning_time.minute)) <= 30
            )
            
            is_evening_commute = (
                settings['evening_commute']['enabled'] and
                abs((current_time.hour * 60 + current_time.minute) - 
                    (evening_time.hour * 60 + evening_time.minute)) <= 30
            )
            
            if is_morning_commute or is_evening_commute:
                try:
                    result = await self.check_weather_for_route(
                        settings['home_address'],
                        settings['work_address']
                    )
                    
                    if result['success']:
                        commute_type = "morning" if is_morning_commute else "evening"
                        
                        if result['will_rain']:
                            message = f"""
🌧️ **Rain Alert for Your {commute_type.title()} Commute!**

📍 **Route**: {settings['home_address']} → {settings['work_address']}

⚠️ **Rain is expected** along your route.

💡 **Recommendation**: Consider taking public transport or driving today.

🕐 **Time**: {current_time.strftime('%H:%M')}
                            """
                        else:
                            message = f"""
☀️ **Great Weather for Your {commute_type.title()} Commute!**

📍 **Route**: {settings['home_address']} → {settings['work_address']}

✅ **No rain expected** on your route.

🚴‍♂️ **Perfect for cycling!**

🕐 **Time**: {current_time.strftime('%H:%M')}
                            """
                        
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                except Exception as e:
                    logger.error(f"Error sending weather alert to user {user_id}: {e}")
    
    def run(self):
        """Run the bot"""
        # Create application
        application = Application.builder().token(self.token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("weather", self.weather_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        # Add job queue for daily weather checks
        job_queue = application.job_queue
        job_queue.run_repeating(
            self.daily_weather_check,
            interval=timedelta(minutes=30),  # Check every 30 minutes
            first=10  # Start after 10 seconds
        )
        
        # Start the bot
        logger.info("Starting MotoRain Telegram Bot...")
        application.run_polling()

def main():
    """Main function"""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    # Create and run bot
    bot = MotoRainTelegramBot(token)
    bot.run()

if __name__ == '__main__':
    main()
