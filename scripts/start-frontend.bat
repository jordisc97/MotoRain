@echo off
echo Starting MotoRain Frontend Server...
echo.
echo This will start the frontend HTTP server on port 3000
echo The application will be available at http://localhost:3000
echo.
pause

cd frontend
python -m http.server 3000

pause
