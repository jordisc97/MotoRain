# Bot Version
BOT_VERSION = "0.2.5"

# Backend API URL (adjust if needed)
BACKEND_BASE_URL = "http://localhost:8001"

# State definitions for conversation handlers
(
    USER_NAME,
    HOME_ADDRESS,
    WORK_ADDRESS,
    SELECTING_ROUTE,
    SETTING_TIMES,
    SETTING_DAYS,
    CONFIRMING_SCHEDULE,
    MANAGING_SCHEDULES,
    EDITING_SCHEDULE_TIME,
    EDITING_SCHEDULE_DAYS,
) = range(10)

# Emojis for weather conditions
RAIN_EMOJIS = ["🌧️", "🌦️", "☔"]
NO_RAIN_EMOJIS = ["☀️"]
CHECKING_EMOJIS = ["🛰️", "📡"]