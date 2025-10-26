@echo off
echo Starting MotoRain Backend Server...
echo.
echo This will start the FastAPI backend server on port 8000
echo Make sure you have activated your virtual environment first!
echo.
pause

cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

pause
