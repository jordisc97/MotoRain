@echo off
TITLE MotoRain Service Manager
echo =================================================
echo ==      MotoRain Services Startup Script       ==
echo =================================================
echo.

REM ===============================
REM [1/3] STOP ANY RUNNING SERVICES
REM ===============================
echo [1/3] Stopping any previously running services...
echo.

echo    - Closing any open service windows...
taskkill /f /fi "WINDOWTITLE eq MotoRain Backend" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq MotoRain Telegram Bot" >nul 2>&1
echo.

echo    - Stopping backend server by port (8001)...
for /f "tokens=5" %%A in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":8001"') do (
    if not "%%A"=="0" (
        echo      Found backend process with PID %%A. Terminating...
        taskkill /F /PID %%A >nul 2>&1
    )
)
echo.

echo    - Killing any Python processes running backend or bot scripts...
for /f "tokens=2 delims=," %%A in ('tasklist /fo csv /nh ^| findstr /i "python.exe"') do (
    for /f "tokens=2 delims==" %%B in ('wmic process where "processid=%%A" get commandline /value 2^>nul ^| findstr /i "bot.py app_mobile uvicorn"') do (
        echo      Found Python process PID %%A related to MotoRain. Terminating...
        taskkill /F /PID %%A >nul 2>&1
    )
)
for /f "tokens=2 delims=," %%A in ('tasklist /fo csv /nh ^| findstr /i "py.exe"') do (
    for /f "tokens=2 delims==" %%B in ('wmic process where "processid=%%A" get commandline /value 2^>nul ^| findstr /i "bot.py app_mobile uvicorn"') do (
        echo      Found Py process PID %%A related to MotoRain. Terminating...
        taskkill /F /PID %%A >nul 2>&1
    )
)
echo.

echo    - Killing any lingering chromedriver.exe processes...
taskkill /F /IM chromedriver.exe /T >nul 2>&1
echo.

echo All previous processes have been stopped.
echo.

REM ===============================
REM [2/3] START BACKEND
REM ===============================
echo [2/3] Starting Backend Server...
echo    - A new window titled 'MotoRain Backend' will open.
START "MotoRain Backend" cmd /k "cd backend && py main.py"
echo.
echo    - Waiting 10 seconds for the backend to initialize...
timeout /t 10 /nobreak >nul
echo.

REM ===============================
REM [3/3] START TELEGRAM BOT
REM ===============================
echo [3/3] Starting Telegram Bot...
echo    - A new window titled 'MotoRain Telegram Bot' will open.
START "MotoRain Telegram Bot" cmd /k "cd telegram_bot && py bot.py"
echo.

echo =================================================
echo ==  All services have been started.            ==
echo ==  You can now close this window.             ==
echo =================================================
echo.
pause
