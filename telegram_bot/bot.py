# HOW TO RUN THIS BOT:
#
# This bot requires the backend server to be running simultaneously.
# You will need to open TWO separate terminals.
#
# Terminal 1: Start the Backend Server
# -------------------------------------
# In your project's root directory (MotoRain-1), run:
#
# > cd backend
# > py -m uvicorn app_mobile:app --host 127.0.0.1 --port 8001
#
# Keep this terminal open.
#
# Terminal 2: Start the Telegram Bot
# -----------------------------------
# In your project's root directory (MotoRain-1), run:
#
# > cd telegram_bot
# > py bot.py
#
# The bot should now be running and responding to commands on Telegram.

import os
import base64
import io
import logging
import random
import asyncio
from typing import Dict
from datetime import datetime

from dotenv import load_dotenv
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

# Import from our new modules
from api import check_rain_api
from constants import (
    BOT_VERSION,
    USER_NAME,
    HOME_ADDRESS,
    WORK_ADDRESS,
    RAIN_EMOJIS,
    NO_RAIN_EMOJIS,
    CHECKING_EMOJIS,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token (loaded from .env file)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in .env file or environment variables")

# In-memory storage (replace with a database for production)
user_data: Dict[int, Dict] = {}
saved_routes: Dict[int, Dict] = {}


# --- Conversation Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for user name."""
    user_id = update.effective_user.id
    user_data[user_id] = {}
    logger.info(f"User {user_id} started a conversation")

    await update.message.reply_text(
        f"🌧️ Welcome to MotoRain Bot v{BOT_VERSION}!\n\n"
        "I'll help you check if it will rain during your commute.\n\n"
        "First, what's your name?"
    )
    return USER_NAME


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store user name and ask for home address."""
    user_id = update.effective_user.id
    user_name = update.message.text.strip()
    user_data[user_id]['user'] = user_name

    await update.message.reply_text(
        f"Nice to meet you, {user_name}! 🏠\n\n"
        "Now, please provide your home address."
    )
    return HOME_ADDRESS


async def get_home_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store home address and ask for work address."""
    user_id = update.effective_user.id
    home_address = update.message.text.strip()
    user_data[user_id]['home'] = home_address

    await update.message.reply_text(
        f"Home address saved: {home_address} ✅\n\n"
        "Now, please provide your work address."
    )
    return WORK_ADDRESS


async def get_work_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store work address and process the rain check."""
    user_id = update.effective_user.id
    work_address = update.message.text.strip()
    user_data[user_id]['work'] = work_address

    await update.message.reply_text(f"Work address saved: {work_address} ✅")

    # Show an interactive "checking" message
    sent_message = await update.message.reply_text(f"{CHECKING_EMOJIS[0]} Checking the weather for you...")
    animation_task = asyncio.create_task(_animate_checking_message(sent_message))

    try:
        current_user_data = user_data[user_id]
        result = await check_rain_api(
            user=current_user_data['user'],
            home=current_user_data['home'],
            work=current_user_data['work'],
        )

        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass  # Task was cancelled as expected

        await sent_message.delete()

        if result.get('status') == 'ok':
            await _send_rain_check_result(update.message, result, current_user_data)
        else:
            await update.message.reply_text(
                "[X] Error: Could not process your request.\nPlease try again later."
            )
            if user_id in user_data:
                del user_data[user_id]

    except Exception as e:
        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass
        await sent_message.edit_text(f"[X] An error occurred: {e}\n\nPlease try again or contact support.")
        logger.error(f"Error processing rain check: {e}", exc_info=True)
        if user_id in user_data:
            del user_data[user_id]

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]

    await update.message.reply_text(
        "[X] Operation cancelled.\n\n"
        "Use /start to begin again."
    )
    return ConversationHandler.END


# --- Command Handlers ---

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
        "/test - Test if bot is responding"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')


async def routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's saved routes via a command."""
    await _show_saved_routes(update.message, user_id=update.effective_user.id)


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command to verify bot is working."""
    logger.info(f"Test command received from user {update.effective_user.id}")
    await update.message.reply_text("✅ Bot is working!")


# --- Callback Query Handlers (Button Clicks) ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main dispatcher for all callback queries."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    user_id = update.effective_user.id

    actions = {
        "check_again": _handle_check_again,
        "save_route": _handle_save_route,
        "my_routes": _handle_my_routes,
        "schedule": _handle_schedule,
        "stop_schedule": _handle_stop_schedule,
        "back_to_main": _handle_back_to_main,
    }

    if action in actions:
        await actions[action](query, context)
    elif action.startswith("use_route_"):
        await _handle_use_route(query, action)
    else:
        logger.warning(f"Unhandled callback action: {action}")


async def _handle_check_again(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    current_user_data = user_data.get(user_id)

    if not current_user_data:
        await query.edit_message_text("[X] No route data found. Please use /start.")
        return

    await query.edit_message_text(f"{CHECKING_EMOJIS[0]} Checking the weather for you...")
    animation_task = asyncio.create_task(_animate_checking_message(query.message))

    try:
        result = await check_rain_api(
            user=current_user_data['user'],
            home=current_user_data['home'],
            work=current_user_data['work'],
        )

        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass

        if result.get('status') == 'ok':
            await _send_rain_check_result(query, result, current_user_data, is_update=True)
        else:
            await query.edit_message_text("[X] Error: Could not re-process your request.")
    except Exception as e:
        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass
        logger.error(f"Error in _handle_check_again: {e}", exc_info=True)
        await query.edit_message_text(f"[X] An error occurred: {e}")


async def _handle_save_route(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    current_user_data = user_data.get(user_id)

    if not current_user_data:
        await query.edit_message_text("[X] No route data to save. Use /start first.")
        return

    if user_id not in saved_routes:
        saved_routes[user_id] = []
    
    route_data = {
        'home': current_user_data['home'],
        'work': current_user_data['work'],
    }
    route_name = f"{route_data['home']} → {route_data['work']}"

    # Avoid saving duplicate routes
    if not any(r['home'] == route_data['home'] and r['work'] == route_data['work'] for r in saved_routes[user_id]):
        saved_routes[user_id].append({
            'name': route_name,
            **route_data,
            'saved_at': datetime.now().isoformat()
        })
        await query.edit_message_text(f"✅ Route saved!\n\n<b>Route:</b> {route_name}", parse_mode='HTML')
    else:
        await query.edit_message_text("ℹ️ This route is already saved.")


async def _handle_my_routes(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
    await _show_saved_routes(query.message, user_id=query.from_user.id, from_callback=True)


async def _handle_schedule(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'schedule' button to set up recurring checks."""
    user_id = query.from_user.id
    current_user_data = user_data.get(user_id)

    if not current_user_data or 'home' not in current_user_data:
        await query.edit_message_text(
            "[X] No route data found. Please use /start to set a route first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]])
        )
        return

    # Check if a job is already running for this user
    job_name = f"rain_check_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    
    keyboard_buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]

    if current_jobs:
        keyboard_buttons.insert(0, [InlineKeyboardButton("❌ Stop Scheduled Checks", callback_data="stop_schedule")])
        await query.edit_message_text(
            "ℹ️ You already have a scheduled rain check running.",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
        return

    # Schedule a repeating job (every 2 minutes for testing)
    context.job_queue.run_repeating(
        _scheduled_rain_check,
        interval=120,
        first=1,
        user_id=user_id,
        data={'user_data': current_user_data},
        name=job_name
    )

    await query.edit_message_text(
        "✅ Scheduled! I will check for rain on your route every 2 minutes.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Stop Scheduled Checks", callback_data="stop_schedule")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ])
    )


async def _handle_stop_schedule(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Stops the scheduled rain checks for the user."""
    user_id = query.from_user.id
    job_name = f"rain_check_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)

    if not current_jobs:
        await query.edit_message_text(
            "ℹ️ You don't have any scheduled checks running.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]])
        )
        return

    for job in current_jobs:
        job.schedule_removal()

    await query.edit_message_text(
        "✅ Your scheduled rain checks have been stopped.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]])
    )


async def _handle_use_route(query: Update.callback_query, action: str):
    user_id = query.from_user.id
    try:
        route_idx = int(action.split("_")[-1])
        if user_id in saved_routes and route_idx < len(saved_routes[user_id]):
            route = saved_routes[user_id][route_idx]
            user_data[user_id] = {
                'user': query.from_user.first_name or "User",
                'home': route['home'],
                'work': route['work'],
            }
            
            await query.edit_message_text(f"{CHECKING_EMOJIS[0]} Checking the weather for you...")
            animation_task = asyncio.create_task(_animate_checking_message(query.message))
            
            try:
                result = await check_rain_api(**user_data[user_id])

                animation_task.cancel()
                try:
                    await animation_task
                except asyncio.CancelledError:
                    pass
                
                if result.get('status') == 'ok':
                    await _send_rain_check_result(query, result, user_data[user_id])
                else:
                    await query.edit_message_text("[X] Error processing saved route.")
            except Exception as e:
                animation_task.cancel()
                try:
                    await animation_task
                except asyncio.CancelledError:
                    pass
                logger.error(f"Error in _handle_use_route for user {user_id}: {e}", exc_info=True)
                await query.edit_message_text(f"[X] An error occurred: {e}")
        else:
            await query.edit_message_text("[X] Saved route not found.")
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing use_route action '{action}': {e}")
        await query.edit_message_text("[X] Invalid route selected.")


async def _animate_checking_message(message):
    """Animates the 'checking' message by cycling through emojis."""
    i = 0
    while True:
        try:
            emoji = CHECKING_EMOJIS[i % len(CHECKING_EMOJIS)]
            await message.edit_text(f"{emoji} Checking the weather for you...")
            await asyncio.sleep(1)
            i += 1
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Could not animate message: {e}")
            break


async def _handle_back_to_main(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
    await query.edit_message_text(
        "What would you like to do next?",
        reply_markup=_get_main_action_buttons()
    )


# --- Helper Functions ---

async def _send_rain_check_result(query, result: Dict, user_info: Dict, is_update: bool = False):
    """Sends the formatted rain check result to the user."""
    image_data = base64.b64decode(result['image_b64'])
    image_file = io.BytesIO(image_data)
    image_file.name = 'radar_map.png'

    will_rain = result['will_rain']
    weather_condition = result['weather_condition']
    
    emoji = random.choice(RAIN_EMOJIS) if will_rain else random.choice(NO_RAIN_EMOJIS)
    status_text = "⚠️ RAIN EXPECTED" if will_rain else "✅ NO RAIN EXPECTED"
    title = f"Rain Check Results {'(Updated)' if is_update else ''}"

    # Create a more conversational and less redundant message
    if will_rain:
        status_line = f"Heads up! <b>{weather_condition.lower()}</b> is expected on your route from <b>{user_info['home']}</b> to <b>{user_info['work']}</b>."
    else:
        status_line = f"Good news! The forecast shows <b>{weather_condition.lower()}</b> for your route from <b>{user_info['home']}</b> to <b>{user_info['work']}</b>."

    message = (
        f"{emoji} <b>{title}</b>\n\n"
        f"{status_line}"
    )

    # When sending a new result, we reply to the original message.
    # When editing (e.g., from a callback), we use the query message.
    target_message = query.message if hasattr(query, 'message') else query
    
    await target_message.reply_photo(
        photo=image_file,
        caption=message,
        parse_mode='HTML'
    )
    
    await target_message.reply_text(
        "What would you like to do next?",
        reply_markup=_get_main_action_buttons()
    )

async def _show_saved_routes(message, user_id: int, from_callback: bool = False):
    """Displays the user's saved routes."""
    user_routes = saved_routes.get(user_id)
    if not user_routes:
        text = "📋 You don't have any saved routes yet."
        keyboard_buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    else:
        text = "📋 <b>Your Saved Routes:</b>\n\n"
        keyboard_buttons = []
        for idx, route in enumerate(user_routes[:5]):  # Max 5 routes
            text += f"{idx + 1}. {route['name']}\n\n"
            keyboard_buttons.append(
                [InlineKeyboardButton(f"Check Route {idx + 1}", callback_data=f"use_route_{idx}")]
            )
        keyboard_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

    if from_callback:
        await message.edit_text(text, parse_mode='HTML', reply_markup=reply_markup)
    else:
        await message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)


async def _scheduled_rain_check(context: ContextTypes.DEFAULT_TYPE):
    """Job function for scheduled rain checks."""
    user_id = context.job.user_id
    user_info = context.job.data.get('user_data', {})

    if not user_info:
        logger.warning(f"Scheduled job for user {user_id} is missing user_data.")
        return

    logger.info(f"Running scheduled rain check for user {user_id}")
    try:
        result = await check_rain_api(
            user=user_info.get('user', 'User'),
            home=user_info.get('home'),
            work=user_info.get('work'),
        )

        if result.get('status') == 'ok':
            will_rain = result['will_rain']
            weather_condition = result['weather_condition']
            
            emoji = random.choice(RAIN_EMOJIS) if will_rain else random.choice(NO_RAIN_EMOJIS)
            status_text = "⚠️ RAIN EXPECTED" if will_rain else "✅ NO RAIN EXPECTED"
            title = "Scheduled Rain Check"

            # Create a more conversational and less redundant message
            if will_rain:
                status_line = f"Heads up! <b>{weather_condition.lower()}</b> is expected on your route from <b>{user_info.get('home')}</b> to <b>{user_info.get('work')}</b>."
            else:
                status_line = f"Good news! The forecast shows <b>{weather_condition.lower()}</b> for your route from <b>{user_info.get('home')}</b> to <b>{user_info.get('work')}</b>."

            message = (
                f"{emoji} <b>{title}</b>\n\n"
                f"{status_line}"
            )
            
            image_data = base64.b64decode(result['image_b64'])
            image_file = io.BytesIO(image_data)
            image_file.name = 'radar_map.png'

            await context.bot.send_photo(
                chat_id=user_id,
                photo=image_file,
                caption=message,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=user_id, 
                text="[X] Error: Could not process your scheduled rain check."
            )
    except Exception as e:
        logger.error(f"Error in _scheduled_rain_check for user {user_id}: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"[X] An error occurred during the scheduled check: {e}"
        )


def _get_main_action_buttons() -> InlineKeyboardMarkup:
    """Returns the main action buttons keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Check Again", callback_data="check_again"),
            InlineKeyboardButton("💾 Save Current Route", callback_data="save_route"),
        ],
        [
            InlineKeyboardButton("⚙️ Schedule Auto Checks", callback_data="schedule"),
            InlineKeyboardButton("📋 View Saved Routes", callback_data="my_routes"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Error & Startup Handlers ---

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and notify the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ Sorry, an unexpected error occurred.")


async def post_init(application: Application) -> None:
    """Post-initialization function to clean up webhooks."""
    logger.info("Running post-init cleanup...")
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook cleanup complete.")


def main() -> None:
    """Start the bot."""
    # Create application with the post_init hook
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Define handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)],
            HOME_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_address)],
            WORK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_work_address)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('test', test_command))
    application.add_handler(CommandHandler('routes', routes_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info(f"Starting MotoRain Telegram Bot v{BOT_VERSION}...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    logger.info("Initializing MotoRain Telegram Bot...")
    main()
