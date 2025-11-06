import os
import base64
import io
import asyncio
import logging
from typing import Dict
from datetime import datetime, timedelta
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Version
BOT_VERSION = "0.0.2"

# Telegram Bot Token
TELEGRAM_TOKEN = "8477567862:AAH2l1W3WztMZI5cbSY5W0oK0r4X7kRZKcg"

# Backend API URL (adjust if needed)
BACKEND_API_URL = "http://localhost:8000/check_rain/"

# Conversation states
(USER_NAME, HOME_ADDRESS, WORK_ADDRESS) = range(3)

# Store user data temporarily
user_data: Dict[int, Dict] = {}

# Store saved routes for users (in production, use a database)
saved_routes: Dict[int, Dict] = {}

# Store scheduled checks for users (in production, use a database)
scheduled_checks: Dict[int, Dict] = {}

# Scheduler for automatic checks
scheduler = AsyncIOScheduler()

# Store application instance for scheduled checks
app_instance = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for user name."""
    try:
        user_id = update.effective_user.id
        user_data[user_id] = {}
        
        logger.info(f"User {user_id} started a conversation")
        
        await update.message.reply_text(
            f"🌧️ Welcome to MotoRain Bot v{BOT_VERSION}!\n\n"
            "I'll help you check if it will rain during your commute.\n\n"
            "Please provide the following information:\n\n"
            "First, what's your name?"
        )
        return USER_NAME
    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}", exc_info=True)
        if update.message:
            await update.message.reply_text(
                "❌ An error occurred. Please try again."
            )
        return ConversationHandler.END


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store user name and ask for home address."""
    user_id = update.effective_user.id
    user_name = update.message.text.strip()
    user_data[user_id]['user'] = user_name
    
    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton("🏠 Continue", callback_data="continue_name"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_conv"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Nice to meet you, {user_name}! 🏠\n\n"
        "Now, please provide your home address:\n"
        "(e.g., 'Barcelona, Spain' or 'Carrer Example 123, Barcelona')",
        reply_markup=reply_markup
    )
    return HOME_ADDRESS


async def get_home_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store home address and ask for work address."""
    user_id = update.effective_user.id
    home_address = update.message.text.strip()
    user_data[user_id]['home'] = home_address
    
    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton("🏢 Continue", callback_data="continue_home"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_conv"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Home address saved: {home_address} ✅\n\n"
        "Now, please provide your work address:\n"
        "(e.g., 'Terrassa, Spain' or 'Carrer Work 456, Terrassa')",
        reply_markup=reply_markup
    )
    return WORK_ADDRESS


async def get_work_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store work address and process the rain check."""
    user_id = update.effective_user.id
    work_address = update.message.text.strip()
    user_data[user_id]['work'] = work_address
    
    # Show processing message
    await update.message.reply_text(
        f"Work address saved: {work_address} ✅\n\n"
        "⏳ Processing your request...\n"
        "Checking radar data and analyzing your route..."
    )
    
    # Process the rain check directly (no vehicle type needed)
    try:
        result = await check_rain_api(
            user=user_data[user_id]['user'],
            home=user_data[user_id]['home'],
            work=user_data[user_id]['work'],
            vehicle="bike"  # Default, not used anymore
        )
        
        if result['status'] == 'ok':
            # Decode the image
            image_data = base64.b64decode(result['image_b64'])
            image_file = io.BytesIO(image_data)
            image_file.name = 'radar_map.png'
            
            # Prepare response message with rain intensity
            will_rain = result['will_rain']
            rain_intensity = result.get('rain_intensity', 'None')
            weather_condition = result['weather_condition']
            
            # Determine emoji and status based on rain intensity
            if rain_intensity == "Heavy":
                emoji = "🌧️"
                status_emoji = "⚠️"
                status_text = "HEAVY RAIN EXPECTED"
                recommendation = "⚠️ Heavy rain expected! Consider taking alternative transportation or postpone your trip."
            elif rain_intensity == "Light":
                emoji = "🌦️"
                status_emoji = "⚠️"
                status_text = "LIGHT RAIN EXPECTED"
                recommendation = "🌦️ Light rain expected. Bring rain gear and ride carefully."
            else:
                emoji = "☀️"
                status_emoji = "✅"
                status_text = "NO RAIN EXPECTED"
                recommendation = "☀️ No rain expected. Safe to ride! Enjoy your commute."
            
            message = (
                f"{emoji} <b>Weather Forecast for Your Commute</b>\n\n"
                f"{status_emoji} <b>{status_text}</b>\n"
                f"📊 {weather_condition}\n\n"
                f"📍 <b>Route:</b> {user_data[user_id]['home']} → {user_data[user_id]['work']}\n\n"
                f"💡 <b>Recommendation:</b> {recommendation}\n\n"
                f"🗺️ Below is the radar map showing weather conditions along your route:"
            )
            
            # Send image with caption
            await update.message.reply_photo(
                photo=image_file,
                caption=message,
                parse_mode='HTML'
            )
            
            # Add action buttons after showing results
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Check Again", callback_data="check_again"),
                    InlineKeyboardButton("💾 Save Route", callback_data="save_route"),
                ],
                [
                    InlineKeyboardButton("⚙️ Schedule Checks", callback_data="schedule"),
                    InlineKeyboardButton("📋 My Routes", callback_data="my_routes"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=reply_markup
            )
            
            # Store user data for potential reuse (save route, check again, etc.)
            # Don't delete it yet - keep it for quick actions
            
        else:
            await update.message.reply_text(
                "❌ Error: Could not process your request.\n"
                "Please try again later."
            )
            # Clean up user data on error
            if user_id in user_data:
                del user_data[user_id]
            
    except Exception as e:
        logger.error(f"Error processing rain check: {str(e)}")
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}\n\n"
            "Please try again or contact support."
        )
        # Clean up user data on error
        if user_id in user_data:
            del user_data[user_id]
    
    return ConversationHandler.END




async def check_rain_api(user: str, home: str, work: str, vehicle: str) -> Dict:
    """Call the backend API to check rain conditions."""
    payload = {
        "user": user,
        "home": home,
        "work": work,
        "vehicle": vehicle
    }
    
    def _make_request():
        """Synchronous function to make the API request."""
        response = requests.post(BACKEND_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    
    try:
        # Run the synchronous request in a thread pool to avoid blocking
        # Use run_in_executor for Python 3.8+ compatibility
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _make_request)
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        raise Exception(f"Failed to connect to backend API: {str(e)}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text(
        "❌ Operation cancelled.\n\n"
        "Use /start to begin again."
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        f"🌧️ <b>MotoRain Bot v{BOT_VERSION} Help</b>\n\n"
        "This bot helps you check if it will rain during your commute.\n\n"
        "<b>Commands:</b>\n"
        "/start - Start a new rain check\n"
        "/weather - Get current radar map (no route check)\n"
        "/routes - View your saved routes\n"
        "/cancel - Cancel the current operation\n"
        "/help - Show this help message\n"
        "/test - Test if bot is responding\n\n"
        "<b>How it works:</b>\n"
        "1. Provide your name\n"
        "2. Enter your home address\n"
        "3. Enter your work address\n"
        "4. Receive a radar map and rain prediction\n\n"
        "<b>After getting results:</b>\n"
        "🔄 <b>Check Again</b> - Re-check weather with same route\n"
        "💾 <b>Save Route</b> - Save route for quick access\n"
        "⚙️ <b>Schedule Checks</b> - Set up automatic checks (coming soon)\n"
        "📋 <b>My Routes</b> - View and use saved routes\n\n"
        "The bot analyzes real-time radar data to predict rain along your route."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current radar map without checking a route."""
    try:
        await update.message.reply_text("⏳ Fetching current radar map...")
        
        # Call backend API to get radar map
        radar_map_url = BACKEND_API_URL.replace('/check_rain/', '/radar_map/')
        
        def _make_request():
            """Synchronous function to make the API request."""
            response = requests.get(radar_map_url, timeout=60)
            response.raise_for_status()
            return response.json()
        
        # Run the synchronous request in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _make_request)
        
        if result['status'] == 'ok':
            # Decode the image
            image_data = base64.b64decode(result['image_b64'])
            image_file = io.BytesIO(image_data)
            image_file.name = 'radar_map.png'
            
            timeframe = result.get('timeframe', 'Current')
            
            message = (
                f"🗺️ <b>Current Radar Map</b>\n\n"
                f"📊 <b>Timeframe:</b> {timeframe}\n\n"
                f"This is the current weather radar map. You can use it to check weather conditions in your area.\n\n"
                f"Use /start to check weather for a specific route."
            )
            
            await update.message.reply_photo(
                photo=image_file,
                caption=message,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Error: Could not fetch radar map.")
    except Exception as e:
        logger.error(f"Error in weather command: {str(e)}")
        await update.message.reply_text(
            f"❌ An error occurred: {str(e)}\n\n"
            "Please try again later."
        )


async def routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's saved routes."""
    user_id = update.effective_user.id
    
    if user_id in saved_routes and saved_routes[user_id]:
        routes_text = "📋 <b>Your Saved Routes:</b>\n\n"
        keyboard_buttons = []
        
        for idx, route in enumerate(saved_routes[user_id][:5]):  # Show max 5 routes
            routes_text += f"{idx + 1}. {route['name']}\n\n"
            keyboard_buttons.append([
                InlineKeyboardButton(f"Check Route {idx + 1}", callback_data=f"use_route_{idx}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
        
        await update.message.reply_text(routes_text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            "📋 You don't have any saved routes yet.\n\n"
            "After checking the weather, use the '💾 Save Route' button to save your route for quick access."
        )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to verify bot is working."""
    logger.info(f"Test command received from user {update.effective_user.id}")
    await update.message.reply_text(
        "✅ Bot is working! The bot is responding correctly.\n\n"
        "Use /start to begin a rain check."
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from action buttons."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    if action == "continue_name" or action == "continue_home":
        # Just acknowledge the continue button - user should type their response
        await query.answer("Please type your response in the chat")
        return
    
    if action == "cancel_conv":
        # Cancel the conversation
        if user_id in user_data:
            del user_data[user_id]
        await query.edit_message_text(
            "❌ Operation cancelled.\n\n"
            "Use /start to begin again."
        )
        return ConversationHandler.END
    
    if action == "check_again":
        # Re-check with the same route data
        if user_id in user_data and all(key in user_data[user_id] for key in ['user', 'home', 'work']):
            await query.edit_message_text("⏳ Checking weather again...")
            
            try:
                result = await check_rain_api(
                    user=user_data[user_id]['user'],
                    home=user_data[user_id]['home'],
                    work=user_data[user_id]['work']
                )
                
                if result['status'] == 'ok':
                    image_data = base64.b64decode(result['image_b64'])
                    image_file = io.BytesIO(image_data)
                    image_file.name = 'radar_map.png'
                    
                    will_rain = result['will_rain']
                    rain_intensity = result.get('rain_intensity', 'None')
                    weather_condition = result['weather_condition']
                    
                    # Determine emoji and status based on rain intensity
                    if rain_intensity == "Heavy":
                        emoji = "🌧️"
                        status_emoji = "⚠️"
                        status_text = "HEAVY RAIN EXPECTED"
                        recommendation = "⚠️ Heavy rain expected! Consider taking alternative transportation or postpone your trip."
                    elif rain_intensity == "Light":
                        emoji = "🌦️"
                        status_emoji = "⚠️"
                        status_text = "LIGHT RAIN EXPECTED"
                        recommendation = "🌦️ Light rain expected. Bring rain gear and ride carefully."
                    else:
                        emoji = "☀️"
                        status_emoji = "✅"
                        status_text = "NO RAIN EXPECTED"
                        recommendation = "☀️ No rain expected. Safe to ride! Enjoy your commute."
                    
                    message = (
                        f"{emoji} <b>Weather Forecast (Updated)</b>\n\n"
                        f"{status_emoji} <b>{status_text}</b>\n"
                        f"📊 {weather_condition}\n\n"
                        f"📍 <b>Route:</b> {user_data[user_id]['home']} → {user_data[user_id]['work']}\n\n"
                        f"💡 <b>Recommendation:</b> {recommendation}\n\n"
                        f"🗺️ Updated radar map showing current weather conditions:"
                    )
                    
                    await query.message.reply_photo(
                        photo=image_file,
                        caption=message,
                        parse_mode='HTML'
                    )
                    
                    # Show action buttons again
                    keyboard = [
                        [
                            InlineKeyboardButton("🔄 Check Again", callback_data="check_again"),
                            InlineKeyboardButton("💾 Save Route", callback_data="save_route"),
                        ],
                        [
                            InlineKeyboardButton("⚙️ Schedule Checks", callback_data="schedule"),
                            InlineKeyboardButton("📋 My Routes", callback_data="my_routes"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("What would you like to do next?", reply_markup=reply_markup)
                else:
                    await query.edit_message_text("❌ Error: Could not process your request.")
            except Exception as e:
                logger.error(f"Error in check_again: {str(e)}")
                await query.edit_message_text(f"❌ An error occurred: {str(e)}")
        else:
            await query.edit_message_text("❌ No route data found. Please use /start to create a new check.")
    
    elif action == "save_route":
        # Save the current route
        if user_id in user_data and all(key in user_data[user_id] for key in ['user', 'home', 'work']):
            if user_id not in saved_routes:
                saved_routes[user_id] = []
            
            route_name = f"{user_data[user_id]['home']} → {user_data[user_id]['work']}"
            route_data = {
                'name': route_name,
                'home': user_data[user_id]['home'],
                'work': user_data[user_id]['work'],
                'saved_at': datetime.now().isoformat()
            }
            
            # Check if route already exists
            existing = [r for r in saved_routes[user_id] if r['home'] == route_data['home'] and r['work'] == route_data['work']]
            if not existing:
                saved_routes[user_id].append(route_data)
                await query.edit_message_text(
                    f"✅ Route saved!\n\n"
                    f"<b>Route:</b> {route_name}\n\n"
                    f"You can now use /routes to quickly check this route again.",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text("ℹ️ This route is already saved.")
        else:
            await query.edit_message_text("❌ No route data found. Please use /start to create a new check.")
    
    elif action == "my_routes":
        # Show saved routes
        if user_id in saved_routes and saved_routes[user_id]:
            routes_text = "📋 <b>Your Saved Routes:</b>\n\n"
            keyboard_buttons = []
            
            for idx, route in enumerate(saved_routes[user_id][:5]):  # Show max 5 routes
                routes_text += f"{idx + 1}. {route['name']}\n\n"
                keyboard_buttons.append([
                    InlineKeyboardButton(f"Check {idx + 1}", callback_data=f"use_route_{idx}")
                ])
            
            keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            
            await query.edit_message_text(routes_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await query.edit_message_text("📋 You don't have any saved routes yet.\n\nUse 'Save Route' after a weather check to save it for quick access.")
    
    elif action == "schedule":
        # Schedule automatic checks
        if user_id in user_data and all(key in user_data[user_id] for key in ['user', 'home', 'work']):
            # Show schedule options
            keyboard = [
                [
                    InlineKeyboardButton("🧪 Test (15 min)", callback_data="schedule_test"),
                    InlineKeyboardButton("📅 Daily Schedule", callback_data="schedule_daily"),
                ],
                [
                    InlineKeyboardButton("📋 My Schedules", callback_data="my_schedules"),
                    InlineKeyboardButton("🔙 Back", callback_data="back_to_main"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚙️ <b>Schedule Automatic Checks</b>\n\n"
                "Choose an option:\n\n"
                "🧪 <b>Test (15 min)</b> - Test mode: Check every 15 minutes\n"
                "📅 <b>Daily Schedule</b> - Set up daily commute checks\n"
                "📋 <b>My Schedules</b> - View your active schedules",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                "❌ No route data found. Please use /start to create a check first."
            )
    
    elif action == "schedule_test":
        # Schedule test checks every 15 minutes
        if user_id in user_data and all(key in user_data[user_id] for key in ['user', 'home', 'work']):
            # Store schedule
            schedule_id = f"{user_id}_test"
            scheduled_checks[user_id] = {
                'schedule_id': schedule_id,
                'type': 'test',
                'interval_minutes': 15,
                'user': user_data[user_id]['user'],
                'home': user_data[user_id]['home'],
                'work': user_data[user_id]['work'],
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            # Schedule the job
            scheduler.add_job(
                perform_scheduled_check,
                trigger=IntervalTrigger(minutes=15),
                id=schedule_id,
                args=[user_id],
                replace_existing=True
            )
            
            await query.edit_message_text(
                "✅ <b>Test Schedule Activated!</b>\n\n"
                "🧪 The bot will now check your route every 15 minutes.\n\n"
                f"📍 <b>Route:</b> {user_data[user_id]['home']} → {user_data[user_id]['work']}\n\n"
                "You'll receive a notification each time a check is performed.\n\n"
                "Use '📋 My Schedules' to view or stop this schedule.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ No route data found. Please use /start first.")
    
    elif action == "my_schedules":
        # Show user's scheduled checks
        if user_id in scheduled_checks:
            schedule = scheduled_checks[user_id]
            schedule_text = (
                "📋 <b>Your Active Schedules:</b>\n\n"
                f"🧪 <b>Type:</b> {schedule['type'].title()}\n"
                f"⏰ <b>Interval:</b> Every {schedule.get('interval_minutes', 15)} minutes\n"
                f"📍 <b>Route:</b> {schedule['home']} → {schedule['work']}\n"
                f"🕐 <b>Created:</b> {datetime.fromisoformat(schedule['created_at']).strftime('%Y-%m-%d %H:%M')}\n"
                f"✅ <b>Status:</b> {'Active' if schedule.get('active', True) else 'Inactive'}\n\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("🛑 Stop Schedule", callback_data="stop_schedule")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(schedule_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await query.edit_message_text(
                "📋 You don't have any active schedules.\n\n"
                "Use '⚙️ Schedule Checks' to set up automatic checks."
            )
    
    elif action == "stop_schedule":
        # Stop scheduled checks
        if user_id in scheduled_checks:
            schedule = scheduled_checks[user_id]
            schedule_id = schedule.get('schedule_id', f"{user_id}_test")
            
            # Remove job from scheduler
            try:
                scheduler.remove_job(schedule_id)
            except Exception as e:
                logger.error(f"Error removing job: {str(e)}")
            
            # Mark as inactive
            scheduled_checks[user_id]['active'] = False
            del scheduled_checks[user_id]
            
            await query.edit_message_text(
                "🛑 <b>Schedule Stopped</b>\n\n"
                "Automatic checks have been disabled.\n\n"
                "You can set up a new schedule anytime using '⚙️ Schedule Checks'.",
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text("❌ No active schedule found.")
    
    elif action == "schedule_daily":
        # Daily schedule (coming soon)
        await query.edit_message_text(
            "📅 <b>Daily Schedule</b>\n\n"
            "This feature is coming soon!\n\n"
            "For now, use '🧪 Test (15 min)' to test automatic checks.",
            parse_mode='HTML'
        )
    
    elif action.startswith("use_route_"):
        # Use a saved route
        route_idx = int(action.split("_")[-1])
        if user_id in saved_routes and route_idx < len(saved_routes[user_id]):
            route = saved_routes[user_id][route_idx]
            # Restore user data from saved route
            user_data[user_id] = {
                'user': update.effective_user.first_name or "User",
                'home': route['home'],
                'work': route['work']
            }
            
            await query.edit_message_text(f"⏳ Checking weather for saved route: {route['name']}...")
            
            # Perform the check
            try:
                result = await check_rain_api(
                    user=user_data[user_id]['user'],
                    home=user_data[user_id]['home'],
                    work=user_data[user_id]['work']
                )
                
                if result['status'] == 'ok':
                    image_data = base64.b64decode(result['image_b64'])
                    image_file = io.BytesIO(image_data)
                    image_file.name = 'radar_map.png'
                    
                    will_rain = result['will_rain']
                    rain_intensity = result.get('rain_intensity', 'None')
                    weather_condition = result['weather_condition']
                    
                    # Determine emoji and status based on rain intensity
                    if rain_intensity == "Heavy":
                        emoji = "🌧️"
                        status_emoji = "⚠️"
                        status_text = "HEAVY RAIN EXPECTED"
                        recommendation = "⚠️ Heavy rain expected! Consider taking alternative transportation or postpone your trip."
                    elif rain_intensity == "Light":
                        emoji = "🌦️"
                        status_emoji = "⚠️"
                        status_text = "LIGHT RAIN EXPECTED"
                        recommendation = "🌦️ Light rain expected. Bring rain gear and ride carefully."
                    else:
                        emoji = "☀️"
                        status_emoji = "✅"
                        status_text = "NO RAIN EXPECTED"
                        recommendation = "☀️ No rain expected. Safe to ride! Enjoy your commute."
                    
                    message = (
                        f"{emoji} <b>Weather Forecast for Your Commute</b>\n\n"
                        f"{status_emoji} <b>{status_text}</b>\n"
                        f"📊 {weather_condition}\n\n"
                        f"📍 <b>Route:</b> {route['name']}\n\n"
                        f"💡 <b>Recommendation:</b> {recommendation}\n\n"
                        f"🗺️ Radar map showing weather conditions along your route:"
                    )
                    
                    await query.message.reply_photo(
                        photo=image_file,
                        caption=message,
                        parse_mode='HTML'
                    )
                    
                    # Show action buttons
                    keyboard = [
                        [
                            InlineKeyboardButton("🔄 Check Again", callback_data="check_again"),
                            InlineKeyboardButton("💾 Save Route", callback_data="save_route"),
                        ],
                        [
                            InlineKeyboardButton("⚙️ Schedule Checks", callback_data="schedule"),
                            InlineKeyboardButton("📋 My Routes", callback_data="my_routes"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("What would you like to do next?", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error using saved route: {str(e)}")
                await query.edit_message_text(f"❌ An error occurred: {str(e)}")
    
    elif action == "back_to_main":
        # Go back to main menu
        keyboard = [
            [
                InlineKeyboardButton("🔄 Check Again", callback_data="check_again"),
                InlineKeyboardButton("💾 Save Route", callback_data="save_route"),
            ],
            [
                InlineKeyboardButton("⚙️ Schedule Checks", callback_data="schedule"),
                InlineKeyboardButton("📋 My Routes", callback_data="my_routes"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("What would you like to do next?", reply_markup=reply_markup)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Try to send error message to user if update is available
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Sorry, an error occurred. Please try again or use /start to begin."
            )
        except Exception:
            pass  # Ignore errors when trying to send error message


def main():
    """Start the bot."""
    try:
        logger.info("Initializing MotoRain Telegram Bot...")
        
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add error handler first
        application.add_error_handler(error_handler)
        
        # Add command handlers BEFORE conversation handler (so they work outside conversations)
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('test', test_command))
        application.add_handler(CommandHandler('routes', routes_command))
        application.add_handler(CommandHandler('weather', weather_command))
        
        # Add conversation handler FIRST (before callback handler to avoid conflicts)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)],
                HOME_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_address)],
                WORK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_work_address)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        application.add_handler(conv_handler)
        
        # Add callback query handler for action buttons AFTER conversation handler
        application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(check_again|save_route|schedule|my_routes|use_route_|back_to_main|continue_name|continue_home|cancel_conv|schedule_test|schedule_daily|my_schedules|stop_schedule)"))
        
        # Store application reference for scheduled checks
        global app_instance
        app_instance = application
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started for automatic checks")
        
        # Start the bot
        logger.info(f"Starting MotoRain Telegram Bot v{BOT_VERSION}...")
        logger.info("Bot is now running. Press Ctrl+C to stop.")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Drop pending updates on startup
        )
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        print(f"\n❌ Error starting bot: {str(e)}")
        print("Please check:")
        print("1. Is the Telegram token correct?")
        print("2. Is python-telegram-bot installed? (pip install python-telegram-bot)")
        print("3. Are there any network issues?")
        raise


if __name__ == '__main__':
    main()

