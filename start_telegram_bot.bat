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

:: --- Run PowerShell cleanup (fast + reliable) ---
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Write-Host '   - Closing any open service windows...';" ^
    "taskkill /f /fi 'WINDOWTITLE eq MotoRain Backend' *> $null 2>&1;" ^
    "taskkill /f /fi 'WINDOWTITLE eq MotoRain Telegram Bot' *> $null 2>&1;" ^
    "" ^
    "Write-Host '   - Stopping backend server by port (8001)...';" ^
    "$backendProc = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue;" ^
    "if ($backendProc) { Write-Host ('      Found backend process on port 8001 with PID ' + $backendProc.OwningProcess + '. Terminating...'); Stop-Process -Id $backendProc.OwningProcess -Force -ErrorAction SilentlyContinue }" ^
    "" ^
    "Write-Host '   - Killing any lingering Python processes (bot.py, uvicorn, app_mobile)...';" ^
    "Get-WmiObject Win32_Process -Filter \"name = 'python.exe' or name = 'py.exe'\" | Where-Object { $_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*app_mobile*' -or $_.CommandLine -like '*uvicorn*' } | ForEach-Object { Write-Host ('      Found process PID ' + $_.ProcessId + '. Terminating...'); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" ^
    "" ^
    "Write-Host '   - Cleanup complete. All previous MotoRain processes stopped.'"

echo.
echo All previous processes have been stopped.
echo.

REM ===============================
REM [2/3] START BACKEND
REM ===============================
echo [2/3] Starting Backend Server...
echo    - A new window titled 'MotoRain Backend' will open.
START "MotoRain Backend" cmd /k "cd backend && py -m uvicorn app_mobile:app --host 127.0.0.1 --port 8001"

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
