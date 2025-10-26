@echo off
echo Starting MotoRain Application...
echo.
echo This will start both the backend and frontend servers
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Make sure you have:
echo 1. Activated your Python virtual environment
echo 2. Installed all requirements (pip install -r backend/requirements.txt)
echo 3. Updated ChromeDriver path in backend/app.py
echo.
pause

echo Starting Backend Server...
start "MotoRain Backend" cmd /k "cd backend && python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload"

echo Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak >nul

echo Starting Frontend Server...
start "MotoRain Frontend" cmd /k "cd frontend && python -m http.server 3000"

echo.
echo Both servers are starting up...
echo Backend will be available at: http://localhost:8000
echo Frontend will be available at: http://localhost:3000
echo.
echo Press any key to open the application in your browser...
pause

start http://localhost:3000

echo.
echo Application opened in browser!
echo Close the command windows to stop the servers.
pause
