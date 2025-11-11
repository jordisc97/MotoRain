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
from datetime import datetime, timedelta, time
import sys
import os
import pandas as pd
import re
import pytz

# Add project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.forecast_checker import MeteoCatTemperatureScraper
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
    JobQueue,
)
from apscheduler.triggers.cron import CronTrigger

# Import from our new modules
from api import check_rain_api, trigger_scrape_api, geocode_address_api
from constants import (
    BOT_VERSION,
    USER_NAME,
    HOME_ADDRESS,
    WORK_ADDRESS,
    RAIN_EMOJIS,
    NO_RAIN_EMOJIS,
    CHECKING_EMOJIS,
    SELECTING_ROUTE,
    SETTING_TIMES,
    SETTING_DAYS,
    CONFIRMING_SCHEDULE,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
logging.getLogger('telegram.ext').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Telegram Bot Token (loaded from .env file)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in .env file or environment variables")

# In-memory storage (replace with a database for production)
user_data: Dict[int, Dict] = {}
saved_routes: Dict[int, Dict] = {}
scheduled_commutes: Dict[int, Dict] = {}
initial_scrape_done = asyncio.Event()


# --- Wrapper for Initial Scrape ---
async def scrape_and_set_event():
    """Calls the scrape API and sets an event upon completion."""
    logger.info("Initial scrape process started.")
    try:
        await trigger_scrape_api()
        initial_scrape_done.set()
        logger.info("Initial scrape process completed and event is set.")
    except Exception as e:
        logger.error(f"Initial scrape failed: {e}", exc_info=True)
        # Still set the event to prevent the bot from hanging on startup
        initial_scrape_done.set()


# --- Conversation Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for user name."""
    user_id = update.effective_user.id
    user_data[user_id] = {}
    logger.info(f"User {user_id} started a conversation")

    # If the initial scrape is still running, show a waiting message.
    if not initial_scrape_done.is_set():
        logger.info("Initial scrape not finished, showing waiting message to user.")
        sent_message = await update.message.reply_text(f"{CHECKING_EMOJIS[0]} Checking the weather for you...")
        animation_task = asyncio.create_task(_animate_checking_message(sent_message))
        
        try:
            # Wait for the initial scrape to complete
            await initial_scrape_done.wait()
            logger.info("Initial scrape finished, proceeding with /start command.")
        finally:
            animation_task.cancel()
            try:
                await animation_task
            except asyncio.CancelledError:
                pass  # Task cancellation is expected
            await sent_message.delete()

    # Stop any existing scheduled jobs for this user
    user_job_prefix = f"commute_{user_id}"
    jobs_to_remove = [job for job in context.job_queue.jobs() if job.name.startswith(user_job_prefix)]
    if jobs_to_remove:
        for job in jobs_to_remove:
            job.schedule_removal()
        logger.info(f"Stopped {len(jobs_to_remove)} scheduled job(s) for user {user_id}")

    await update.message.reply_text(
        f"🏍️🌧️ Welcome to MotoRain Bot v{BOT_VERSION}!\n\n"
        "I'll help you dodge the rain on your commute. Here's what I can do:\n\n"
        "  - 🌦️ Get a Detailed Forecast: Check the temperature, wind, and rain for your specific route and time.\n"
        "  - ⏰ Look Ahead 24 Hours: I'll warn you if any rain is expected in the next 24 hours.\n"
        "  - 💾 Save Your Routes: Save your favorite commutes for quick and easy checks later.\n\n"
        "To get started, what's your name?"
    )
    return USER_NAME


async def get_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store user name and ask for home address."""
    user_id = update.effective_user.id
    user_name = update.message.text.strip()
    user_data[user_id]['user'] = user_name

    await update.message.reply_text(
        f"Nice to meet you, {user_name}! 🏠\n\n"
        "Now, please provide your home address.\n"
        "For best results, use the format: `Street, City` (e.g., `Carrer de Balmes, Barcelona`).",
        parse_mode='Markdown'
    )
    return HOME_ADDRESS


async def get_home_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store home address and ask for work address, with validation."""
    user_id = update.effective_user.id
    home_address = update.message.text.strip()

    # Validate address
    sent_message = await update.message.reply_text("🔍 Validating address...")
    result = await geocode_address_api(home_address)
    await sent_message.delete()

    if result.get("status") != "ok":
        error_message = result.get("error", "Invalid address. Please try again.")
        await update.message.reply_text(f"⚠️ {error_message}")
        # Ask for home address again
        return HOME_ADDRESS

    user_data[user_id]['home'] = home_address

    await update.message.reply_text(
        f"Home address saved: {home_address} ✅\n\n"
        "Now, please provide your work address.\n"
        "For best results, use the format: `Street, City` (e.g., `Avinguda Diagonal, Barcelona`).",
        parse_mode='Markdown'
    )
    return WORK_ADDRESS


async def get_work_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store work address and process the rain check, with validation."""
    user_id = update.effective_user.id
    work_address = update.message.text.strip()

    # Validate address
    sent_message = await update.message.reply_text("🔍 Validating address...")
    result = await geocode_address_api(work_address)
    await sent_message.delete()

    if result.get("status") != "ok":
        error_message = result.get("error", "Invalid address. Please try again.")
        await update.message.reply_text(f"⚠️ {error_message}")
        # Ask for work address again
        return WORK_ADDRESS
        
    user_data[user_id]['work'] = work_address

    await update.message.reply_text(f"Work address saved: {work_address} ✅")

    # Now, check the weather. If the initial scrape isn't done, wait for it.
    sent_message = await update.message.reply_text(f"{CHECKING_EMOJIS[0]} Checking the weather for you...")
    animation_task = asyncio.create_task(_animate_checking_message(sent_message))

    try:
        # Wait for initial scrape if it's not done yet.
        if not initial_scrape_done.is_set():
            logger.info("Initial scrape not finished, waiting before checking rain.")
            await initial_scrape_done.wait()
            logger.info("Initial scrape finished, proceeding with rain check.")

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

        if result.get('status') == 'ok':
            await sent_message.delete()
            await _send_rain_check_result(update, result, current_user_data)
        else:
            await sent_message.delete()
            error_message = result.get('error', 'Could not process your request.')
            await update.message.reply_text(f"[X] Error: {error_message}\nPlease try again later.")
            if user_id in user_data:
                del user_data[user_id]

    except Exception as e:
        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass
        if sent_message:
            await sent_message.edit_text(f"[X] An error occurred: {e}\n\nPlease try again or contact support.")
        else:
            await update.message.reply_text(f"[X] An error occurred: {e}\n\nPlease try again or contact support.")
        logger.error(f"Error processing rain check: {e}", exc_info=True)
        if user_id in user_data:
            del user_data[user_id]

    return ConversationHandler.END


async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to schedule commute checks."""
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
        user_id = query.from_user.id
    else:
        message = update.message
        user_id = update.effective_user.id
        
    user_routes = saved_routes.get(user_id)

    if not user_routes:
        await message.reply_text(
            "You need to have at least one saved route to schedule checks. "
            "Use /start to create a route first."
        )
        return ConversationHandler.END

    keyboard = []
    for idx, route in enumerate(user_routes):
        keyboard.append([InlineKeyboardButton(f"{idx + 1}: {route['name']}", callback_data=f"select_route_{idx}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        # The original message is a photo with a caption, so we can't edit its text.
        # We delete it and send a new message.
        await query.message.delete()
        await query.message.reply_text(
            "Which route do you want to schedule checks for?", reply_markup=reply_markup
        )
    else:
        await message.reply_text("Which route do you want to schedule checks for?", reply_markup=reply_markup)

    return SELECTING_ROUTE


async def select_route_for_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Selects the route and asks for commute times."""
    query = update.callback_query
    await query.answer()
    route_idx = int(query.data.split("_")[-1])

    user_id = query.from_user.id
    context.user_data['route_idx'] = route_idx

    await query.message.reply_text("What time do you usually leave for the office? (e.g., 08:30)")

    return SETTING_TIMES


async def get_commute_times(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the morning commute time and asks for the evening time."""
    morning_time = update.message.text
    context.user_data['morning_time'] = morning_time

    await update.message.reply_text("What time do you usually leave to go back home? (e.g., 17:30)")

    return SETTING_DAYS


async def get_commute_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the evening commute time and asks for the days."""
    evening_time = update.message.text
    context.user_data['evening_time'] = evening_time

    keyboard = [
        [
            InlineKeyboardButton("Mon", callback_data="day_0"),
            InlineKeyboardButton("Tue", callback_data="day_1"),
            InlineKeyboardButton("Wed", callback_data="day_2"),
            InlineKeyboardButton("Thu", callback_data="day_3"),
            InlineKeyboardButton("Fri", callback_data="day_4"),
        ],
        [InlineKeyboardButton("Done", callback_data="day_done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("On which days do you commute? (Select multiple and press Done)", reply_markup=reply_markup)

    context.user_data['days'] = []
    return CONFIRMING_SCHEDULE


async def confirm_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Adds the selected day and shows the confirmation summary."""
    query = update.callback_query
    await query.answer()

    day_action = query.data.split("_")[-1]
    
    if day_action == "done":
        if not context.user_data.get('days'):
            await query.answer("Please select at least one day.")
            return CONFIRMING_SCHEDULE
        return await schedule_summary_and_confirm(update, context)

    day = int(day_action)
    if day not in context.user_data['days']:
        context.user_data['days'].append(day)
    else:
        context.user_data['days'].remove(day)


    days_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    selected_days = ", ".join([days_map[d] for d in sorted(context.user_data['days'])])
    
    route_idx = context.user_data['route_idx']
    route = saved_routes[query.from_user.id][route_idx]
    morning_time = context.user_data['morning_time']
    evening_time = context.user_data['evening_time']

    summary = (
        f"Selected days: {selected_days or 'None'}"
    )

    keyboard = [
        [
            InlineKeyboardButton("Mon", callback_data="day_0"),
            InlineKeyboardButton("Tue", callback_data="day_1"),
            InlineKeyboardButton("Wed", callback_data="day_2"),
            InlineKeyboardButton("Thu", callback_data="day_3"),
            InlineKeyboardButton("Fri", callback_data="day_4"),
        ],
        [InlineKeyboardButton("Done", callback_data="day_done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=summary, reply_markup=reply_markup)

    return CONFIRMING_SCHEDULE


async def schedule_summary_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows the final summary and asks for confirmation."""
    query = update.callback_query
    
    days_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    selected_days = ", ".join([days_map[d] for d in sorted(context.user_data['days'])])

    route_idx = context.user_data['route_idx']
    route = saved_routes[query.from_user.id][route_idx]
    morning_time = context.user_data['morning_time']
    evening_time = context.user_data['evening_time']

    summary = (
        f"Got it! I will check your '{route['name']}' route at {morning_time} "
        f"and your return route at {evening_time} on {selected_days}. Is this correct?"
    )

    keyboard = [
        [
            InlineKeyboardButton("Yes", callback_data="schedule_confirm_yes"),
            InlineKeyboardButton("No", callback_data="schedule_confirm_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text=summary, reply_markup=reply_markup)
    
    return CONFIRMING_SCHEDULE

async def schedule_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the schedule and ends the conversation."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    await query.edit_message_text(
        "Schedule confirmed! I will notify you 30 minutes before your commute if rain is expected.",
        reply_markup=_get_main_action_buttons()
        )
    
    # Store the schedule
    route_idx = context.user_data['route_idx']
    route = saved_routes[user_id][route_idx]
    
    schedule_info = {
        'route': route,
        'morning_time': context.user_data['morning_time'],
        'evening_time': context.user_data['evening_time'],
        'days': context.user_data['days'],
        'active': True
    }
    
    if user_id not in scheduled_commutes:
        scheduled_commutes[user_id] = []
    scheduled_commutes[user_id].append(schedule_info)

    # Here we would call the function to schedule the jobs with the JobQueue
    _schedule_commute_checks(context, user_id, schedule_info)
    
    return ConversationHandler.END


async def schedule_cancelled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the schedule setup."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Schedule setup cancelled.")
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


async def start_new_route_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts a new route conversation from a button press, acting as an entry point."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    
    # Preserve user name if it exists, otherwise clear all data
    existing_user_name = user_data.get(user_id, {}).get('user')
    if existing_user_name:
        user_data[user_id] = {'user': existing_user_name}
    else:
        user_data[user_id] = {}

    # Stop scheduled jobs
    user_job_prefix = f"commute_{user_id}"
    jobs_to_remove = [job for job in context.job_queue.jobs() if job.name.startswith(user_job_prefix)]
    if jobs_to_remove:
        for job in jobs_to_remove:
            job.schedule_removal()
        logger.info(f"User {user_id} started a new route, stopping {len(jobs_to_remove)} scheduled job(s).")

    # Clean up the previous message (the one with the buttons)
    await query.message.delete()

    # If we know the user, ask for home address directly. Otherwise, ask for name.
    if existing_user_name:
        await query.message.reply_text(
            f"Okay, {existing_user_name}, let's add a new route.\n\n"
            "🏠 Please provide the new home address."
        )
        return HOME_ADDRESS
    else:
        await query.message.reply_text(
            "Okay, let's add a new route.\n\n"
            "To get started, what's your name?"
        )
        return USER_NAME


async def reset_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for confirmation to reset user data."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, I'm sure", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Delete the old message and send a new one for confirmation
    await query.message.delete()
    await query.message.reply_text(
        "🗑️ Are you sure you want to delete all your data?\n\n"
        "This will remove all your saved routes and scheduled checks. This action cannot be undone.",
        reply_markup=reply_markup
    )


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
        "back_to_main": _handle_back_to_main,
        "confirm_reset": _handle_confirm_reset,
        "cancel_reset": _handle_cancel_reset,
        "reset": reset_confirmation,
    }

    if action in actions:
        await actions[action](update, context)
    elif action.startswith("use_route_"):
        await _handle_use_route(update, action)
    elif action.startswith("select_route_"):
        await select_route_for_schedule(update, context)
    elif action.startswith("day_"):
        await confirm_schedule(update, context)
    elif action == "schedule_confirm_yes":
        await schedule_confirmed(update, context)
    elif action == "schedule_confirm_no":
        await schedule_cancelled(update, context)
    else:
        logger.warning(f"Unhandled callback action: {action}")


async def _handle_check_again(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    current_user_data = user_data.get(user_id)

    if not current_user_data:
        await query.message.delete()
        await query.message.reply_text("[X] No route data found. Please use /start.")
        return

    # Delete the old photo message and send a new one for the animation
    await query.message.delete()
    sent_message = await query.message.reply_text(f"{CHECKING_EMOJIS[0]} Checking the weather for you...")
    animation_task = asyncio.create_task(_animate_checking_message(sent_message))

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
        
        await sent_message.delete()

        if result.get('status') == 'ok':
            # Send a new photo message (is_update=False because we already deleted the old one)
            await _send_rain_check_result(update, result, current_user_data, is_update=False)
        else:
            await query.message.reply_text("[X] Error: Could not re-process your request.")
    except Exception as e:
        animation_task.cancel()
        try:
            await animation_task
        except asyncio.CancelledError:
            pass
        logger.error(f"Error in _handle_check_again: {e}", exc_info=True)
        await sent_message.delete()
        await query.message.reply_text(f"[X] An error occurred: {e}")


async def _handle_confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes all data for the user."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Stop scheduled jobs
    user_job_prefix = f"commute_{user_id}"
    jobs_to_remove = [job for job in context.job_queue.jobs() if job.name.startswith(user_job_prefix)]
    if jobs_to_remove:
        for job in jobs_to_remove:
            job.schedule_removal()
        logger.info(f"Deleted {len(jobs_to_remove)} scheduled jobs for user {user_id} during reset.")

    # Delete from in-memory storage
    if user_id in user_data:
        del user_data[user_id]
    if user_id in saved_routes:
        del saved_routes[user_id]
    if user_id in scheduled_commutes:
        del scheduled_commutes[user_id]

    keyboard = [[InlineKeyboardButton("🚀 Start New Conversation", callback_data="add_new_route")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    await query.edit_message_text(
        "✅ All your data has been successfully deleted.",
        reply_markup=reply_markup
    )


async def _handle_cancel_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the reset action."""
    query = update.callback_query
    await query.edit_message_text("❌ Reset cancelled.")


async def _handle_save_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    current_user_data = user_data.get(user_id)

    if not current_user_data:
        await query.message.reply_text("[X] No route data to save. Use /start first.")
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
        await query.message.reply_text(
            f"✅ Route saved!\n\n<b>Route:</b> {route_name}",
            parse_mode='HTML',
            reply_markup=_get_main_action_buttons()
        )
    else:
        await query.message.reply_text(
            "ℹ️ This route is already saved.",
            reply_markup=_get_main_action_buttons()
        )
    
    await query.message.delete()


async def _handle_my_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _show_saved_routes(query.message, user_id=query.from_user.id)
    await query.message.delete()


async def _handle_use_route(update: Update, action: str):
    query = update.callback_query
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
                    await _send_rain_check_result(update, result, user_data[user_id])
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


async def _execute_scheduled_check(context: ContextTypes.DEFAULT_TYPE):
    """The function that is called by the job queue."""
    job_data = context.job.data
    user_id = job_data["user_id"]
    commute_time = job_data["commute_time"]
    route_name = job_data["route"]
    user_info = user_data.get(user_id, {})
    
    # If user_info is not in the in-memory dictionary, we can't proceed.
    # A more robust solution would involve a persistent database.
    if not user_info:
        logger.warning(f"Could not find user_info for user {user_id} in memory. Skipping scheduled check.")
        return

    logger.info(f"Running scheduled check for user {user_id} for commute at {commute_time}.")
    
    # Find the correct route from the new structure of saved_routes
    route_to_check = None
    if user_id in saved_routes:
        for route in saved_routes[user_id]:
            if route['name'] == route_name:
                route_to_check = route
                break
    
    if not route_to_check:
        logger.error(f"Could not find route '{route_name}' for user {user_id} during scheduled check.")
        return

    home_address = route_to_check['home']
    work_address = route_to_check['work']

    try:
        # We re-use the same API and result sending logic as the interactive check
        result = await check_rain_api(
            user=user_info.get('user', str(user_id)),
            home=home_address,
            work=work_address,
        )

        if result.get('status') == 'ok':
            # Only send a notification if there is rain, to avoid spamming the user.
            if result.get('will_rain'):
                logger.info(f"Rain detected for user {user_id}. Sending scheduled alert.")
                # We need a `Message` or `CallbackQuery` object to send a reply.
                # Since we don't have one in a scheduled job, we send a new message directly.
                await _send_rain_check_result(
                    context.bot,  # Pass the bot instance
                    result=result,
                    user_info=user_info,
                    is_update=False, # This will be a new message
                    chat_id=user_id # Explicitly provide the chat_id
                )
            else:
                logger.info(f"No rain detected for user {user_id}. No scheduled alert sent.")
        else:
            error_message = result.get('error', 'Could not process your scheduled request.')
            logger.error(f"Error in scheduled check for user {user_id}: {error_message}")

    except Exception as e:
        logger.error(f"Exception in scheduled check for user {user_id}: {e}", exc_info=True)


def _parse_time(time_str: str) -> time:
    """Parses a time string (HH:MM) and returns a time object."""
    try:
        # Handle formats like '9:30' or '09:30'
        dt_obj = datetime.strptime(time_str, "%H:%M")
        return dt_obj.time()
    except ValueError:
        return None

def _schedule_commute_checks(context: ContextTypes.DEFAULT_TYPE, user_id: int, schedule_info: Dict):
    """Schedules the commute checks based on the user's settings."""
    # Remove existing jobs for this user to avoid duplicates
    user_job_prefix = f"commute_{user_id}"
    jobs_to_remove = [job for job in context.job_queue.jobs() if job.name.startswith(user_job_prefix)]
    for job in jobs_to_remove:
        job.schedule_removal()

    morning_time_obj = _parse_time(schedule_info['morning_time'])
    evening_time_obj = _parse_time(schedule_info['evening_time'])
    
    if not morning_time_obj or not evening_time_obj:
        logger.error(f"Invalid time format for user {user_id}")
        return

    days = tuple(schedule_info["days"])
    days_str = ",".join(map(str, days))

    # Define timezone and convert user's local time to UTC for the scheduler
    local_tz = pytz.timezone("Europe/Madrid")

    # Calculate morning check time in UTC
    naive_morning_dt = datetime.now().replace(hour=morning_time_obj.hour, minute=morning_time_obj.minute, second=0, microsecond=0)
    local_morning_dt = local_tz.localize(naive_morning_dt, is_dst=None)
    local_morning_check_dt = local_morning_dt - timedelta(minutes=30)
    utc_morning_check_dt = local_morning_check_dt.astimezone(pytz.utc)

    # Calculate evening check time in UTC
    naive_evening_dt = datetime.now().replace(hour=evening_time_obj.hour, minute=evening_time_obj.minute, second=0, microsecond=0)
    local_evening_dt = local_tz.localize(naive_evening_dt, is_dst=None)
    local_evening_check_dt = local_evening_dt - timedelta(minutes=30)
    utc_evening_check_dt = local_evening_check_dt.astimezone(pytz.utc)
    
    # Schedule the morning check using CronTrigger with UTC time
    context.job_queue.run_custom(
        _execute_scheduled_check,
        name=f"commute_{user_id}_morning",
        data={
            "user_id": user_id,
            "commute_time": schedule_info['morning_time'],
            "route": schedule_info['route']['name'],
            "type": "morning",
            "user_info": user_data[user_id]
        },
        job_kwargs={
            "trigger": CronTrigger(
                day_of_week=days_str, 
                hour=utc_morning_check_dt.hour, 
                minute=utc_morning_check_dt.minute,
                timezone='UTC'
            ),
        }
    )

    # Schedule the evening check using CronTrigger with UTC time
    context.job_queue.run_custom(
        _execute_scheduled_check,
        name=f"commute_{user_id}_evening",
        data={
            "user_id": user_id,
            "commute_time": schedule_info['evening_time'],
            "route": schedule_info['route']['name'],
            "type": "evening",
            "user_info": user_data[user_id]
        },
        job_kwargs={
            "trigger": CronTrigger(
                day_of_week=days_str, 
                hour=utc_evening_check_dt.hour, 
                minute=utc_evening_check_dt.minute,
                timezone='UTC'
            ),
        }
    )

    # Log the scheduled times
    logger.info(
        f"Scheduled commute checks for user {user_id} on days {days} at {schedule_info['morning_time']} "
        f"and {schedule_info['evening_time']} (local time)."
    )


async def _animate_checking_message(message):
    """Animates the 'checking' message by cycling through emojis."""
    i = 1  # Start from the second emoji to avoid re-editing with the same content
    last_text = message.text
    while True:
        try:
            emoji = CHECKING_EMOJIS[i % len(CHECKING_EMOJIS)]
            new_text = f"{emoji} Checking the weather for you..."
            if new_text != last_text:
                await message.edit_text(new_text)
                last_text = new_text
            await asyncio.sleep(1)
            i += 1
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Could not animate message: {e}")
            break


async def _handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.reply_text(
        "What would you like to do next?",
        reply_markup=_get_main_action_buttons()
    )
    await query.message.delete()


# --- Helper Functions ---

async def _get_forecast_data(home: str, work: str, end_time_str: str) -> Dict[str, float] | None:
    """Fetches and processes forecast data for home and work locations."""
    if not end_time_str:
        return None

    try:
        # Determine the target hour for the forecast
        time_match = re.search(r'(\d{2}):\d{2}', end_time_str)
        if not time_match:
            logger.warning(f"Could not parse end_time_str: {end_time_str}")
            return None
        
        target_hour = int(time_match.group(1))
        forecast_time_str = f"{target_hour:02d}:00"
        
        # Initialize scraper
        # The bot runs from `telegram_bot`, so we go one level up for the backend path
        municipalities_path = os.path.join(project_root, 'backend', 'municipalities.json')
        scraper = MeteoCatTemperatureScraper(municipalities_json_path=municipalities_path)

        # Asynchronously get weather data for both locations
        home_df, work_df = await asyncio.gather(
            asyncio.to_thread(scraper.get_weather_by_name, home),
            asyncio.to_thread(scraper.get_weather_by_name, work)
        )

        # Process dataframes to find the forecast for the target hour
        results = []
        for df in [home_df, work_df]:
            if df.empty:
                continue

            # Filter for the specific time
            row = df[df['Time'] == forecast_time_str]
            if not row.empty:
                try:
                    temp = pd.to_numeric(row['Temperatura (°C)'].iloc[0], errors='coerce')
                    rain = pd.to_numeric(row['Precipitació acumulada (mm)'].iloc[0], errors='coerce')
                    wind = pd.to_numeric(row['Vent (km/h)'].iloc[0].split()[0], errors='coerce') # Take first part of "2 NE"
                    
                    if pd.notna(temp) and pd.notna(rain) and pd.notna(wind):
                        results.append({'temp': temp, 'rain': rain, 'wind': wind})
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse weather data row: {row}. Error: {e}")
                    continue

        if not results:
            logger.info("No valid forecast data found for the specified time.")
            return None

        # Calculate averages
        avg_temp = sum(r['temp'] for r in results) / len(results)
        avg_rain = sum(r['rain'] for r in results) / len(results)
        avg_wind = sum(r['wind'] for r in results) / len(results)

        # Check for rain in the next 24 hours
        rain_warning = None
        combined_df = pd.concat([home_df, work_df]).drop_duplicates().reset_index(drop=True)
        if not combined_df.empty:
            try:
                # Convert day/time to datetime objects for comparison
                combined_df['timestamp'] = pd.to_datetime(
                    combined_df['Day'] + ' ' + combined_df['Time'], 
                    format='%d/%m/%y %H:%M',
                    errors='coerce'
                )
                combined_df.dropna(subset=['timestamp'], inplace=True)
                
                now = datetime.now()
                in_24_hours = now + timedelta(hours=24)
                
                future_df = combined_df[
                    (combined_df['timestamp'] > now) & 
                    (combined_df['timestamp'] <= in_24_hours)
                ].copy() # Use .copy() to avoid SettingWithCopyWarning
                
                future_df.loc[:, 'Precipitació acumulada (mm)'] = pd.to_numeric(
                    future_df['Precipitació acumulada (mm)'], errors='coerce'
                )
                rainy_hours = future_df[future_df['Precipitació acumulada (mm)'] > 0]
                
                if not rainy_hours.empty:
                    # Find the first hour with rain
                    first_rain_hour = rainy_hours.sort_values(by='timestamp').iloc[0]
                    rain_time = first_rain_hour['timestamp'].strftime('%H:%M')
                    rain_amount = first_rain_hour['Precipitació acumulada (mm)']
                    rain_warning = f"🌧️ Heads up! Rain is forecast at {rain_time} ({rain_amount} mm)."

            except Exception as e:
                logger.error(f"Error processing 24-hour rain forecast: {e}")


        return {
            'forecast_temperature_avg': round(avg_temp),
            'forecast_accumulated_rain_avg': round(avg_rain, 1),
            'forecast_wind_speed_avg': round(avg_wind),
            'rain_warning_24h': rain_warning
        }

    except ValueError as e:
        # This could be triggered if a municipality is not found
        logger.error(f"Could not get forecast data due to ValueError: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in _get_forecast_data: {e}", exc_info=True)
        return None

async def _send_rain_check_result(update, result: Dict, user_info: Dict, is_update: bool = False, chat_id: int = None):
    """Sends the formatted rain check result to the user."""
    image_data = base64.b64decode(result['image_b64'])
    image_file = io.BytesIO(image_data)
    image_file.name = 'radar_map.png'

    will_rain = result['will_rain']
    rain_intensity = result.get('rain_intensity', 'None')
    start_time = result.get('start_time')
    end_time = result.get('end_time')

    # Get forecast data
    forecast = await _get_forecast_data(user_info['home'], user_info['work'], end_time)

    emoji = random.choice(RAIN_EMOJIS) if will_rain else random.choice(NO_RAIN_EMOJIS)
    title = f"Rain Check Results {'(Updated)' if is_update else ''}"
    
    # Format the message components
    route_line = f"<b>Route:</b> {user_info['home']} → {user_info['work']}"
    time_line = f"<b>Time:</b> {start_time} → {end_time}" if start_time and end_time else ""

    if will_rain:
        condition_line = f"<b>Condition:</b> {rain_intensity.title()} Rain"
    else:
        condition_line = "<b>Condition:</b> No rain"

    # Build message body
    body_parts = [route_line]
    if time_line:
        body_parts.append(time_line)
    body_parts.append(condition_line)
    
    # Add forecast data if available
    if forecast:
        body_parts.append("")  # Add an empty line for spacing
        body_parts.append(f"🌡️ <b>Temperature:</b> {forecast['forecast_temperature_avg']}°C")
        body_parts.append(f"💧 <b>Accumulated Rain:</b> {forecast['forecast_accumulated_rain_avg']} mm")
        body_parts.append(f"💨 <b>Wind:</b> {forecast['forecast_wind_speed_avg']} km/h")

    # Add 24-hour rain warning if available
    if forecast:
        body_parts.append("")  # Add an empty line for spacing
        if forecast.get('rain_warning_24h'):
            body_parts.append(forecast['rain_warning_24h'])
        else:
            body_parts.append("✅ No rain expected in the next 24 hours.")

    message = f"{emoji} <b>{title}</b>\n\n" + "\n".join(body_parts)

    # Determine the target to reply to or send message to
    if isinstance(update, Update):
        target = update.effective_message
        bot = update.get_bot()
        final_chat_id = target.chat_id
    else: # Assuming 'update' is a bot instance for scheduled tasks
        bot = update
        final_chat_id = chat_id
        target = None

    if not final_chat_id:
        logger.error("Could not determine chat_id to send message.")
        return

    # If updating, delete the old message and send a new one with the photo
    if is_update and target:
        await target.delete()

    await bot.send_photo(
        chat_id=final_chat_id,
        photo=image_file,
        caption=message,
        parse_mode='HTML',
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
        ],
        [
            InlineKeyboardButton("➕ Add New Route", callback_data="add_new_route"),
            InlineKeyboardButton("🗑️ Reset Conversation", callback_data="reset"),
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
    
    # Trigger a scrape on startup to ensure fresh data
    logger.info("Triggering initial data scrape.")
    asyncio.create_task(scrape_and_set_event())
    
    logger.info("Webhook cleanup complete.")


def main() -> None:
    """Start the bot."""
    job_queue = JobQueue()

    # Create application with the post_init hook
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .job_queue(job_queue)
        .build()
    )

    # Define handlers
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(start_new_route_from_button, pattern='^add_new_route$')
        ],
        states={
            USER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_name)],
            HOME_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_address)],
            WORK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_work_address)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
        per_user=True
    )

    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('test', test_command))
    application.add_handler(CommandHandler('routes', routes_command))
    
    schedule_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('schedule', schedule_start),
            CallbackQueryHandler(schedule_start, pattern='^schedule$')
            ],
        states={
            SELECTING_ROUTE: [CallbackQueryHandler(select_route_for_schedule, pattern='^select_route_')],
            SETTING_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_commute_times)],
            SETTING_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_commute_days)],
            CONFIRMING_SCHEDULE: [
                CallbackQueryHandler(confirm_schedule, pattern='^day_'),
                CallbackQueryHandler(schedule_confirmed, pattern='^schedule_confirm_yes$'),
                CallbackQueryHandler(schedule_cancelled, pattern='^schedule_confirm_no$'),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
        per_user=True
    )
    application.add_handler(schedule_conv_handler)

    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info(f"Starting MotoRain Telegram Bot v{BOT_VERSION}...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    logger.info("Initializing MotoRain Telegram Bot...")
    main()
