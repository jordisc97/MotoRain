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
from datetime import datetime, timedelta
import sys
import os
import pandas as pd
import re

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
)

# Import from our new modules
from api import check_rain_api, trigger_scrape_api
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

    # Stop any existing scheduled jobs for this user
    job_name = f"rain_check_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        logger.info(f"Stopped {len(current_jobs)} scheduled job(s) for user {user_id}")

    # Trigger a background scrape on the backend without waiting for it to complete.
    # This helps ensure the data is fresh by the time the user provides their route.
    logger.info("Triggering a background radar scrape.")
    asyncio.create_task(trigger_scrape_api())

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
        elif result.get('status') == 404:
            error_message = result.get('error', 'A location could not be found.')
            await update.message.reply_text(error_message)
            if user_id in user_data:
                del user_data[user_id]
        else:
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
    job_name = f"rain_check_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        logger.info(f"User {user_id} started a new route, stopping {len(current_jobs)} scheduled job(s).")

    # Trigger a background scrape
    logger.info("Triggering a background radar scrape for new route.")
    asyncio.create_task(trigger_scrape_api())

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
    query = update
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
        "schedule": _handle_schedule,
        "stop_schedule": _handle_stop_schedule,
        "back_to_main": _handle_back_to_main,
        "confirm_reset": _handle_confirm_reset,
        "cancel_reset": _handle_cancel_reset,
        "reset": reset_confirmation,
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
            await _send_rain_check_result(query.message, result, current_user_data, is_update=False)
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


async def _handle_confirm_reset(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Deletes all data for the user."""
    user_id = query.from_user.id
    
    # Stop scheduled jobs
    job_name = f"rain_check_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        logger.info(f"Deleted {len(current_jobs)} scheduled jobs for user {user_id} during reset.")

    # Delete from in-memory storage
    if user_id in user_data:
        del user_data[user_id]
    if user_id in saved_routes:
        del saved_routes[user_id]

    keyboard = [[InlineKeyboardButton("🚀 Start New Conversation", callback_data="add_new_route")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
        
    await query.edit_message_text(
        "✅ All your data has been successfully deleted.",
        reply_markup=reply_markup
    )


async def _handle_cancel_reset(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
    """Cancels the reset action."""
    await query.edit_message_text("❌ Reset cancelled.")


async def _handle_save_route(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
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


async def _handle_my_routes(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
    await _show_saved_routes(query.message, user_id=query.from_user.id)
    await query.message.delete()


async def _handle_schedule(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'schedule' button to set up recurring checks."""
    user_id = query.from_user.id
    current_user_data = user_data.get(user_id)

    if not current_user_data or 'home' not in current_user_data:
        await query.message.reply_text(
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
        await query.message.reply_text(
            "ℹ️ You already have a scheduled rain check running.",
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )
        await query.message.delete()
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

    await query.message.reply_text(
        "✅ Scheduled! I will check for rain on your route every 2 minutes.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Stop Scheduled Checks", callback_data="stop_schedule")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
        ])
    )
    await query.message.delete()


async def _handle_stop_schedule(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    """Stops the scheduled rain checks for the user."""
    user_id = query.from_user.id
    job_name = f"rain_check_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)

    if not current_jobs:
        await query.message.reply_text(
            "ℹ️ You don't have any scheduled checks running.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]])
        )
        await query.message.delete()
        return

    for job in current_jobs:
        job.schedule_removal()

    await query.message.reply_text(
        "✅ Your scheduled rain checks have been stopped.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]])
    )
    await query.message.delete()


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
    last_text = ""
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


async def _handle_back_to_main(query: Update.callback_query, _: ContextTypes.DEFAULT_TYPE):
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
                    # Find the hour with the most rain
                    max_rain_hour = rainy_hours.loc[rainy_hours['Precipitació acumulada (mm)'].idxmax()]
                    rain_time = max_rain_hour['timestamp'].strftime('%H:%M')
                    rain_amount = max_rain_hour['Precipitació acumulada (mm)']
                    rain_warning = f"🌧️ Heads up! Rain is forecast at {rain_time} ({rain_amount} mm)."

            except Exception as e:
                logger.error(f"Error processing 24-hour rain forecast: {e}")


        return {
            'temperature': round(avg_temp),
            'rain': round(avg_rain, 1),
            'wind': round(avg_wind),
            'rain_warning': rain_warning
        }

    except ValueError as e:
        # This could be triggered if a municipality is not found
        logger.error(f"Could not get forecast data due to ValueError: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in _get_forecast_data: {e}", exc_info=True)
        return None

async def _send_rain_check_result(query, result: Dict, user_info: Dict, is_update: bool = False):
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
        body_parts.append(f"🌡️ <b>Temperature:</b> {forecast['temperature']}°C")
        body_parts.append(f"💧 <b>Accumulated Rain:</b> {forecast['rain']} mm")
        body_parts.append(f"💨 <b>Wind:</b> {forecast['wind']} km/h")

    # Add 24-hour rain warning if available
    if forecast:
        body_parts.append("")  # Add an empty line for spacing
        if forecast.get('rain_warning'):
            body_parts.append(forecast['rain_warning'])
        else:
            body_parts.append("✅ No rain expected in the next 24 hours.")

    message = f"{emoji} <b>{title}</b>\n\n" + "\n".join(body_parts)

    target_message = query.message if hasattr(query, 'message') else query
    
    if is_update:
        await target_message.delete()

    await target_message.reply_photo(
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
            rain_intensity = result.get('rain_intensity', 'None')
            start_time = result.get('start_time')
            end_time = result.get('end_time')
            
            # Get forecast data
            forecast = await _get_forecast_data(user_info.get('home'), user_info.get('work'), end_time)

            emoji = random.choice(RAIN_EMOJIS) if will_rain else random.choice(NO_RAIN_EMOJIS)
            title = "Scheduled Rain Check"

            # Format the message
            route_line = f"<b>Route:</b> {user_info.get('home')} → {user_info.get('work')}"
            time_line = f"<b>Time:</b> {start_time} → {end_time}" if start_time and end_time else ""
            
            if will_rain:
                condition_line = f"<b>Condition:</b> {rain_intensity.title()} Rain"
            else:
                condition_line = "<b>Condition:</b> No rain"

            body_parts = [route_line]
            if time_line:
                body_parts.append(time_line)
            body_parts.append(condition_line)
            
            # Add forecast data if available
            if forecast:
                body_parts.append("")  # Add an empty line for spacing
                body_parts.append(f"🌡️ <b>Temperature:</b> {forecast['temperature']}°C")
                body_parts.append(f"💧 <b>Accumulated Rain:</b> {forecast['rain']} mm")
                body_parts.append(f"💨 <b>Wind:</b> {forecast['wind']} km/h")
            
            # Add 24-hour rain warning if available
            if forecast:
                body_parts.append("")  # Add an empty line for spacing
                if forecast.get('rain_warning'):
                    body_parts.append(forecast['rain_warning'])
                else:
                    body_parts.append("✅ No rain expected in the next 24 hours.")
            
            message = f"{emoji} <b>{title}</b>\n\n" + "\n".join(body_parts)
            
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
    logger.info("Webhook cleanup complete.")


def main() -> None:
    """Start the bot."""
    # Create application with the post_init hook
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

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
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info(f"Starting MotoRain Telegram Bot v{BOT_VERSION}...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    logger.info("Initializing MotoRain Telegram Bot...")
    main()
