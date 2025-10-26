import os
import tempfile
import base64
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from radar_rain_checker import RadarRainChecker

# ------- Configure -------
CHROMEDRIVER_PATH = r"../chromedriver/chromedriver.exe"
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
            "weather_condition": "Rain expected" if will_rain else "No significant rain expected"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in check_rain: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources when the app shuts down."""
    try:
        radar_checker.close()
        print("Radar checker closed successfully")
    except Exception as e:
        print(f"Error closing radar checker: {str(e)}")
