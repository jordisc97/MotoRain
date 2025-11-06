import os
import base64
import io
import asyncio
import logging
from typing import Dict
from datetime import datetime
import requests
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
BOT_VERSION = "0.0.1"

# Telegram Bot Token
TELEGRAM_TOKEN = "8477567862:AAH2l1W3WztMZI5cbSY5W0oK0r4X7kRZKcg"

# Backend API URL (adjust if needed)
BACKEND_API_URL = "http://localhost:8000/check_rain/"

# Conversation states
(USER_NAME, HOME_ADDRESS, WORK_ADDRESS, VEHICLE_TYPE) = range(4)

# Store user data temporarily
user_data: Dict[int, Dict] = {}

# Store saved routes for users (in production, use a database)
saved_routes: Dict[int, Dict] = {}


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
    
    await update.message.reply_text(
        f"Nice to meet you, {user_name}! 🏠\n\n"
        "Now, please provide your home address:\n"
        "(e.g., 'Barcelona, Spain' or 'Carrer Example 123, Barcelona')"
    )
    return HOME_ADDRESS


async def get_home_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store home address and ask for work address."""
    user_id = update.effective_user.id
    home_address = update.message.text.strip()
    user_data[user_id]['home'] = home_address
    
    await update.message.reply_text(
        f"Home address saved: {home_address} ✅\n\n"
        "Now, please provide your work address:\n"
        "(e.g., 'Terrassa, Spain' or 'Carrer Work 456, Terrassa')"
    )
    return WORK_ADDRESS


async def get_work_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store work address and ask for vehicle type."""
    user_id = update.effective_user.id
    work_address = update.message.text.strip()
    user_data[user_id]['work'] = work_address
    
    keyboard = [
        [
            InlineKeyboardButton("🚴 Bike", callback_data="bike"),
            InlineKeyboardButton("🏍️ Motorbike", callback_data="motorbike"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Work address saved: {work_address} ✅\n\n"
        "What vehicle will you use for your commute?",
        reply_markup=reply_markup
    )
    return VEHICLE_TYPE


async def get_vehicle_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store vehicle type and process the rain check."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    vehicle_type = query.data
    user_data[user_id]['vehicle'] = vehicle_type
    
    # Show processing message
    await query.edit_message_text(
        "⏳ Processing your request...\n"
        "Checking radar data and analyzing your route..."
    )
    
    # Call backend API
    try:
        result = await check_rain_api(
            user=user_data[user_id]['user'],
            home=user_data[user_id]['home'],
            work=user_data[user_id]['work'],
            vehicle=vehicle_type
        )
        
        if result['status'] == 'ok':
            # Decode the image
            image_data = base64.b64decode(result['image_b64'])
            image_file = io.BytesIO(image_data)
            image_file.name = 'radar_map.png'
            
            # Prepare response message
            will_rain = result['will_rain']
            weather_condition = result['weather_condition']
            
            emoji = "🌧️" if will_rain else "☀️"
            status_text = "⚠️ RAIN EXPECTED" if will_rain else "✅ NO RAIN EXPECTED"
            
            message = (
                f"{emoji} <b>Rain Check Results</b>\n\n"
                f"<b>Status:</b> {status_text}\n"
                f"<b>Condition:</b> {weather_condition}\n"
                f"<b>Route:</b> {user_data[user_id]['home']} → {user_data[user_id]['work']}\n"
                f"<b>Vehicle:</b> {'🚴 Bike' if vehicle_type == 'bike' else '🏍️ Motorbike'}\n\n"
                f"Here's the radar map showing your route:"
            )
            
            # Send image with caption
            await query.message.reply_photo(
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
            
            await query.message.reply_text(
                "What would you like to do next?",
                reply_markup=reply_markup
            )
            
            # Store user data for potential reuse (save route, check again, etc.)
            # Don't delete it yet - keep it for quick actions
            
        else:
            await query.edit_message_text(
                "❌ Error: Could not process your request.\n"
                "Please try again later."
            )
            # Clean up user data on error
            if user_id in user_data:
                del user_data[user_id]
            
    except Exception as e:
        logger.error(f"Error processing rain check: {str(e)}")
        await query.edit_message_text(
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
        "/routes - View your saved routes\n"
        "/cancel - Cancel the current operation\n"
        "/help - Show this help message\n"
        "/test - Test if bot is responding\n\n"
        "<b>How it works:</b>\n"
        "1. Provide your name\n"
        "2. Enter your home address\n"
        "3. Enter your work address\n"
        "4. Select your vehicle type (bike or motorbike)\n"
        "5. Receive a radar map and rain prediction\n\n"
        "<b>After getting results:</b>\n"
        "🔄 <b>Check Again</b> - Re-check weather with same route\n"
        "💾 <b>Save Route</b> - Save route for quick access\n"
        "⚙️ <b>Schedule Checks</b> - Set up automatic checks (coming soon)\n"
        "📋 <b>My Routes</b> - View and use saved routes\n\n"
        "The bot analyzes real-time radar data to predict rain along your route."
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's saved routes."""
    user_id = update.effective_user.id
    
    if user_id in saved_routes and saved_routes[user_id]:
        routes_text = "📋 <b>Your Saved Routes:</b>\n\n"
        keyboard_buttons = []
        
        for idx, route in enumerate(saved_routes[user_id][:5]):  # Show max 5 routes
            routes_text += f"{idx + 1}. {route['name']}\n"
            routes_text += f"   Vehicle: {'🚴 Bike' if route['vehicle'] == 'bike' else '🏍️ Motorbike'}\n\n"
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
    
    if action == "check_again":
        # Re-check with the same route data
        if user_id in user_data and all(key in user_data[user_id] for key in ['user', 'home', 'work', 'vehicle']):
            await query.edit_message_text("⏳ Checking weather again...")
            
            try:
                result = await check_rain_api(
                    user=user_data[user_id]['user'],
                    home=user_data[user_id]['home'],
                    work=user_data[user_id]['work'],
                    vehicle=user_data[user_id]['vehicle']
                )
                
                if result['status'] == 'ok':
                    image_data = base64.b64decode(result['image_b64'])
                    image_file = io.BytesIO(image_data)
                    image_file.name = 'radar_map.png'
                    
                    will_rain = result['will_rain']
                    weather_condition = result['weather_condition']
                    emoji = "🌧️" if will_rain else "☀️"
                    status_text = "⚠️ RAIN EXPECTED" if will_rain else "✅ NO RAIN EXPECTED"
                    
                    message = (
                        f"{emoji} <b>Rain Check Results (Updated)</b>\n\n"
                        f"<b>Status:</b> {status_text}\n"
                        f"<b>Condition:</b> {weather_condition}\n"
                        f"<b>Route:</b> {user_data[user_id]['home']} → {user_data[user_id]['work']}\n"
                        f"<b>Vehicle:</b> {'🚴 Bike' if user_data[user_id]['vehicle'] == 'bike' else '🏍️ Motorbike'}\n\n"
                        f"Here's the updated radar map:"
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
        if user_id in user_data and all(key in user_data[user_id] for key in ['user', 'home', 'work', 'vehicle']):
            if user_id not in saved_routes:
                saved_routes[user_id] = []
            
            route_name = f"{user_data[user_id]['home']} → {user_data[user_id]['work']}"
            route_data = {
                'name': route_name,
                'home': user_data[user_id]['home'],
                'work': user_data[user_id]['work'],
                'vehicle': user_data[user_id]['vehicle'],
                'saved_at': datetime.now().isoformat()
            }
            
            # Check if route already exists
            existing = [r for r in saved_routes[user_id] if r['home'] == route_data['home'] and r['work'] == route_data['work']]
            if not existing:
                saved_routes[user_id].append(route_data)
                await query.edit_message_text(
                    f"✅ Route saved!\n\n"
                    f"<b>Route:</b> {route_name}\n"
                    f"<b>Vehicle:</b> {'🚴 Bike' if route_data['vehicle'] == 'bike' else '🏍️ Motorbike'}\n\n"
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
                routes_text += f"{idx + 1}. {route['name']}\n"
                routes_text += f"   Vehicle: {'🚴 Bike' if route['vehicle'] == 'bike' else '🏍️ Motorbike'}\n\n"
                keyboard_buttons.append([
                    InlineKeyboardButton(f"Check {idx + 1}", callback_data=f"use_route_{idx}")
                ])
            
            keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            
            await query.edit_message_text(routes_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await query.edit_message_text("📋 You don't have any saved routes yet.\n\nUse 'Save Route' after a weather check to save it for quick access.")
    
    elif action == "schedule":
        # Schedule automatic checks (simplified version)
        await query.edit_message_text(
            "⚙️ <b>Schedule Automatic Checks</b>\n\n"
            "This feature will automatically check the weather before your commute times.\n\n"
            "To set up scheduled checks, you'll need to:\n"
            "1. Set your commute times\n"
            "2. Choose which days to check\n"
            "3. Enable notifications\n\n"
            "This feature is coming soon! For now, you can manually check using /start.",
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
                'work': route['work'],
                'vehicle': route['vehicle']
            }
            
            await query.edit_message_text(f"⏳ Checking weather for saved route: {route['name']}...")
            
            # Perform the check
            try:
                result = await check_rain_api(
                    user=user_data[user_id]['user'],
                    home=user_data[user_id]['home'],
                    work=user_data[user_id]['work'],
                    vehicle=user_data[user_id]['vehicle']
                )
                
                if result['status'] == 'ok':
                    image_data = base64.b64decode(result['image_b64'])
                    image_file = io.BytesIO(image_data)
                    image_file.name = 'radar_map.png'
                    
                    will_rain = result['will_rain']
                    weather_condition = result['weather_condition']
                    emoji = "🌧️" if will_rain else "☀️"
                    status_text = "⚠️ RAIN EXPECTED" if will_rain else "✅ NO RAIN EXPECTED"
                    
                    message = (
                        f"{emoji} <b>Rain Check Results</b>\n\n"
                        f"<b>Status:</b> {status_text}\n"
                        f"<b>Condition:</b> {weather_condition}\n"
                        f"<b>Route:</b> {route['name']}\n"
                        f"<b>Vehicle:</b> {'🚴 Bike' if route['vehicle'] == 'bike' else '🏍️ Motorbike'}\n\n"
                        f"Here's the radar map:"
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
        
        # Add callback query handler for action buttons
        application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(check_again|save_route|schedule|my_routes|use_route_|back_to_main)"))
        
        # Add conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)],
                HOME_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_address)],
                WORK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_work_address)],
                VEHICLE_TYPE: [CallbackQueryHandler(get_vehicle_type)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # Add conversation handler
        application.add_handler(conv_handler)
        
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

