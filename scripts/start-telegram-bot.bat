@echo off
echo Starting MotoRain Telegram Bot...
echo.
echo This will start the Telegram bot
echo Make sure the backend server is running on port 8000!
echo.
pause

cd telegram_bot
python bot.py

pause

