import os
import tempfile
import base64
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from radar_rain_checker import RadarRainChecker
import json

# ------- Configure -------
# ChromeDriver path - set to None to use webdriver-manager (recommended)
# or provide a path to a specific ChromeDriver executable
CHROMEDRIVER_PATH = None  # Will use webdriver-manager to auto-download correct version
MAP_BOUNDS = (40.65, -0.92, 42.95, 4.55)
# -------------------------

app = FastAPI()

# Initialize RadarRainChecker without routes (we'll add them per request)
radar_checker = RadarRainChecker(
    chromedriver_path=CHROMEDRIVER_PATH,
    map_bounds=MAP_BOUNDS,
    headless=True
)

# Flag to track if we've scraped the radar data
radar_data_scraped = False

# Store for scheduled checks (in production, use a database)
scheduled_checks = {}

# Configure CORS
origins = [
    "http://localhost:3000",  # Default React port
    "http://127.0.0.1:3000",  # Localhost alternative
    "http://localhost:8000",  # Default FastAPI port
    "http://127.0.0.1:8000",  # Localhost alternative
    "http://localhost",       # Just in case
    "file://"                 # For file:// protocol when opening directly
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to log requests for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response

class RouteIn(BaseModel):
    user: str
    home: str  # address string
    work: str  # address string
    vehicle: Optional[str] = "bike"  # "bike" or "motorbike"

class ScheduledCheckIn(BaseModel):
    user_id: str
    home: str
    work: str
    commute_times: List[str]  # List of times in HH:MM format
    commute_days: List[str]   # List of days (monday, tuesday, etc.)
    push_token: Optional[str] = None
    vehicle: Optional[str] = "bike"

class NotificationRequest(BaseModel):
    user_id: str
    title: str
    message: str
    notification_type: str  # "rain_alert" or "clear_weather"
    push_token: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the radar checker when the app starts."""
    try:
        print("Opening radar page...")
        radar_checker.open_radar_page()
        print("Scraping radar data...")
        radar_checker.scrape_frames()
        print("Radar data scraped successfully")
        global radar_data_scraped
        radar_data_scraped = True
    except Exception as e:
        print(f"Error initializing radar checker: {str(e)}")
        # Don't raise, allow the server to start even if radar initialization fails

@app.post("/check_rain/")
async def check_rain(route: RouteIn):
    try:
        # Check if we have radar data
        if not radar_data_scraped:
            raise HTTPException(status_code=503, detail="Radar data not available yet. Please try again in a moment.")
            
        # Convert addresses to coordinates
        home_coords = RadarRainChecker.get_coordinates_from_address(route.home)
        work_coords = RadarRainChecker.get_coordinates_from_address(route.work)
        
        # Set the route for this request
        radar_checker.routes = [{"user": route.user, "home": home_coords, "work": work_coords}]
        
        # Process the frames (reusing the already scraped data)
        tmpdir = tempfile.mkdtemp()
        results = radar_checker.process_frames(output_dir=tmpdir)
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to process radar data")
        
        # Get the result for this user
        will_rain = results.get(route.user, False)
        
        # Read and encode the generated map image
        fname = os.path.join(tmpdir, f"{route.user}_map.png")
        if not os.path.exists(fname):
            raise HTTPException(status_code=500, detail="Annotated map not found")
            
        with open(fname, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Return the response
        return {
            "status": "ok",
            "user": route.user,
            "vehicle": route.vehicle,
            "image_b64": img_b64,
            "will_rain": will_rain,
            "weather_condition": "Rain expected" if will_rain else "No significant rain expected",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in check_rain: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/schedule_checks/")
async def schedule_checks(schedule: ScheduledCheckIn, background_tasks: BackgroundTasks):
    """Schedule automatic rain checks for a user's commute times."""
    try:
        # Store the schedule
        scheduled_checks[schedule.user_id] = {
            "home": schedule.home,
            "work": schedule.work,
            "commute_times": schedule.commute_times,
            "commute_days": schedule.commute_days,
            "push_token": schedule.push_token,
            "vehicle": schedule.vehicle,
            "created_at": datetime.now().isoformat()
        }
        
        # Schedule background tasks for each commute time
        for commute_time in schedule.commute_times:
            background_tasks.add_task(
                schedule_background_check,
                schedule.user_id,
                commute_time,
                schedule.commute_days
            )
        
        return {
            "status": "ok",
            "message": f"Scheduled {len(schedule.commute_times)} commute checks",
            "user_id": schedule.user_id
        }
        
    except Exception as e:
        print(f"Error scheduling checks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def schedule_background_check(user_id: str, commute_time: str, commute_days: List[str]):
    """Schedule a background check for a specific commute time."""
    try:
        # Parse commute time (HH:MM format)
        hour, minute = map(int, commute_time.split(':'))
        
        # Calculate check time (30 minutes before commute)
        check_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        check_time -= timedelta(minutes=30)
        
        # If the check time has passed today, schedule for tomorrow
        if check_time <= datetime.now():
            check_time += timedelta(days=1)
        
        print(f"Scheduled background check for user {user_id} at {check_time}")
        
        # In a real implementation, you would use a task scheduler like Celery
        # or APScheduler to handle the actual scheduling
        
    except Exception as e:
        print(f"Error in background check scheduling: {str(e)}")

@app.post("/send_notification/")
async def send_notification(notification: NotificationRequest):
    """Send a push notification to a user."""
    try:
        # In a real implementation, you would integrate with Apple Push Notification Service
        # For now, we'll just log the notification
        
        notification_data = {
            "user_id": notification.user_id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.notification_type,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"Sending notification: {notification_data}")
        
        # Here you would integrate with APNs or Firebase Cloud Messaging
        # Example with APNs:
        # await send_apns_notification(notification.push_token, notification.title, notification.message)
        
        return {
            "status": "ok",
            "message": "Notification sent successfully",
            "notification_id": f"notif_{datetime.now().timestamp()}"
        }
        
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/scheduled_checks/{user_id}")
async def get_scheduled_checks(user_id: str):
    """Get scheduled checks for a user."""
    if user_id not in scheduled_checks:
        raise HTTPException(status_code=404, detail="No scheduled checks found for this user")
    
    return {
        "status": "ok",
        "user_id": user_id,
        "schedule": scheduled_checks[user_id]
    }

@app.delete("/scheduled_checks/{user_id}")
async def delete_scheduled_checks(user_id: str):
    """Delete scheduled checks for a user."""
    if user_id in scheduled_checks:
        del scheduled_checks[user_id]
        return {"status": "ok", "message": "Scheduled checks deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="No scheduled checks found for this user")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "radar_data_available": radar_data_scraped
    }

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources when the app shuts down."""
    try:
        radar_checker.close()
        print("Radar checker closed successfully")
    except Exception as e:
        print(f"Error closing radar checker: {str(e)}")

# Background task to perform scheduled rain checks
async def perform_scheduled_check(user_id: str):
    """Perform a scheduled rain check for a user."""
    try:
        if user_id not in scheduled_checks:
            print(f"No schedule found for user {user_id}")
            return
        
        schedule = scheduled_checks[user_id]
        
        # Create a route request
        route = RouteIn(
            user=user_id,
            home=schedule["home"],
            work=schedule["work"],
            vehicle=schedule["vehicle"]
        )
        
        # Perform the rain check
        result = await check_rain(route)
        
        # Send appropriate notification
        if result["will_rain"]:
            notification = NotificationRequest(
                user_id=user_id,
                title="🌧️ Rain Alert!",
                message=f"Rain expected on your commute: {result['weather_condition']}",
                notification_type="rain_alert",
                push_token=schedule.get("push_token")
            )
        else:
            notification = NotificationRequest(
                user_id=user_id,
                title="✅ Clear Weather",
                message=f"No rain expected on your commute: {result['weather_condition']}",
                notification_type="clear_weather",
                push_token=schedule.get("push_token")
            )
        
        await send_notification(notification)
        
    except Exception as e:
        print(f"Error in scheduled check for user {user_id}: {str(e)}")
