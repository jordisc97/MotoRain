import os
import time
import re
from io import BytesIO
from typing import List, Tuple, Dict, Optional

import numpy as np
import colorsys
import requests
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime, timedelta
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# --- Constants ---
# Bounding box for Catalonia, Spain
# (min_latitude, min_longitude, max_latitude, max_longitude)
CATALUNYA_BOUNDS = (40.65, -0.9, 42.95, 4.55)

class RadarRainChecker:
    """
    Scrape Catalonia radar images, build a composite,
    and check for rain along commute routes for multiple users.
    """

    def __init__(
        self,
        chromedriver_path: str,
        routes: List[Dict] = None,
        map_bounds: Tuple[float, float, float, float] = (40.65, -0.9, 42.95, 4.55),
        headless: bool = True,
    ):
        """
        Initialize the RadarRainChecker.

        Args:
            chromedriver_path (str): Path to ChromeDriver executable.
            routes (List[Dict]): List of user routes, each with 'user', 'home', and 'work' coordinates.
            map_bounds (Tuple[float, float, float, float]): Map bounds (lat_min, lon_min, lat_max, lon_max).
            headless (bool): Whether to run Chrome in headless mode.
        """
        self.routes = routes or []
        self.map_bounds = map_bounds
        self.radar_data: List[Dict] = []
        self.last_composite = None
        self.last_times = []

        # Selenium setup
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        # Use webdriver-manager to automatically download the correct ChromeDriver version
        # If chromedriver_path is provided and exists, use it; otherwise use webdriver-manager
        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
        else:
            # Automatically download and use the correct ChromeDriver version
            service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Font setup for titles and addresses
        for font_name, size in [("seguiemj.ttf", 28), ("arial.ttf", 24)]:
            try:
                self.font = ImageFont.truetype(font_name, size)
                break
            except OSError:
                continue
        else:
            self.font = ImageFont.load_default()

        # Smaller font specifically for emojis
        for font_name, size in [("seguiemj.ttf", 16), ("arial.ttf", 16)]:
            try:
                self.emoji_font = ImageFont.truetype(font_name, size)
                break
            except OSError:
                continue
        else:
            self.emoji_font = self.font  # fallback to main font if emoji font fails

    # ------------------------- UTILITY METHODS -------------------------

    @staticmethod
    def get_coordinates_from_address(address: str) -> Tuple[float, float]:
        """
        Convert an address string into geographic coordinates (latitude, longitude)
        using the Nominatim OpenStreetMap API, biased towards Catalonia.
        """
        url = "https://nominatim.openstreetmap.org/search"
        
        # Add Catalonia context to the query for better accuracy
        if "catalonia" not in address.lower() and "catalunya" not in address.lower():
            query = f"{address}, Catalonia, Spain"
        else:
            query = address

        params = {
            "q": query,
            "format": "json",
            "viewbox": f"{CATALUNYA_BOUNDS[1]},{CATALUNYA_BOUNDS[2]},{CATALUNYA_BOUNDS[3]},{CATALUNYA_BOUNDS[0]}",
            "bounded": 1,
            "limit": 1
        }
        headers = {
            "User-Agent": "MotoRainApp/1.0 (jordi@example.com)",
            "Referer": "http://localhost:8000"
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                raise ValueError(f"No coordinates found for address: {address}")
            return float(data[0]["lat"]), float(data[0]["lon"])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error getting coordinates: {str(e)}")

    def latlon_to_pixels(self, lat: float, lon: float, img_size: Tuple[int, int]) -> Tuple[int, int]:
        """Convert latitude and longitude to pixel coordinates on the radar image."""
        lat_min, lon_min, lat_max, lon_max = self.map_bounds
        width, height = img_size
        x = (lon - lon_min) / (lon_max - lon_min) * width
        y = (lat_max - lat) / (lat_max - lat_min) * height
        return int(x), int(y)

    @staticmethod
    def get_pixel_intensity(pixel: Tuple[int, int, int]) -> int:
        """
        Determine rain intensity from a pixel's color based on the Meteocat legend.
        Returns:
            0: No rain
            1: Light rain (feble: purple, blue, cyan)
            2: Moderate rain (moderada: green, yellow, magenta)
            3: Heavy rain (forta: orange, red)
        """
        r, g, b = pixel[:3]

        # Non-rain colors (background, map features)
        if max(r, g, b) < 50 or min(r, g, b) > 240:  # Dark or light background
            return 0
        if (abs(r - g) < 20) and (abs(r - b) < 20) and (r >= 80) and (r <= 240):  # Gray map features
            return 0

        # Heavy rain (forta: oranges, reds)
        if (r > 180 and 80 <= g < 180 and b < 80) or \
           (r > 180 and g < 80 and b < 80):
            return 3

        # Moderate rain (moderada: greens, yellows, magentas)
        if (g > r + 30 and g > b + 30 and g > 100) or \
           (r > 120 and g > 120 and b < 80) or \
           (r > 120 and g < 120 and b > 120):
            return 2

        # Light rain (feble: purples, blues, cyans)
        if (b > r + 30 and b > g + 10 and b > 120 and g > r):
            return 1

        return 0

    @staticmethod
    def is_rain_color(rgb_pixel: Tuple[int, int, int]) -> bool:
        """Determine whether a pixel color indicates rain based on intensity."""
        return RadarRainChecker.get_pixel_intensity(rgb_pixel) > 0

    def contains_rain_color(self, pixels: List[Tuple[int, int, int]]) -> bool:
        """Check if a list of pixels contains rain."""
        rain_pixels = sum(1 for px in pixels if self.is_rain_color(px))
        return rain_pixels >= (2 if len(pixels) > 10 else 1)

    @staticmethod
    def get_pixels_along_line(img: Image.Image, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int, int]]:
        """Return a list of pixels along a line between two points using Bresenham's algorithm."""
        pixels = []
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        x, y = x0, y0
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)

        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if 0 <= x < img.width and 0 <= y < img.height:
                    pixels.append(img.getpixel((x, y)))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if 0 <= x < img.width and 0 <= y < img.height:
                    pixels.append(img.getpixel((x, y)))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        if 0 <= x1 < img.width and 0 <= y1 < img.height:
            pixels.append(img.getpixel((x1, y1)))
        return pixels

    @staticmethod
    def is_within_bounds(coords: tuple, bounds: tuple) -> bool:
        """Check if a given (latitude, longitude) is within the specified bounds."""
        lat, lon = coords
        min_lat, min_lon, max_lat, max_lon = bounds
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon

    # ------------------------- SCRAPE & COMPOSITE -------------------------

    def open_radar_page(self, url: str = "https://www.meteo.cat/observacions/radar") -> None:
        """Open the Catalonia radar webpage in the browser."""
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "adveccio_slider"))
        )

    def scrape_frames(self) -> None:
        """Scrape all radar frames from the webpage."""
        slider = self.driver.find_element(By.ID, "adveccio_slider")
        map_container = self.driver.find_element(By.CLASS_NAME, "leaflet-container")
        min_val, max_val, step = int(slider.get_attribute("min")), int(slider.get_attribute("max")), int(slider.get_attribute("step"))

        self.radar_data = []
        for val in range(min_val, max_val + step, step):
            self.driver.execute_script(
                f"document.getElementById('adveccio_slider').value = {val};"
                "document.getElementById('adveccio_slider').dispatchEvent(new Event('input'));"
            )
            time.sleep(1.5)
            time_text = self.driver.find_element(By.CLASS_NAME, "time_label").text.strip()
            
            # Extract just the HH:MM part from the time string
            match = re.search(r'(\d{1,2}:\d{2})', time_text)
            formatted_time = match.group(1) if match else time_text

            img = Image.open(BytesIO(map_container.screenshot_as_png)).crop((0, 0, map_container.size['width'], map_container.size['height'] - 50))
            self.radar_data.append({"time": formatted_time, "image": img})
        
        if not self.radar_data:
            print("[RADAR_SCRAPER_WARNING] Scraped 0 frames. The website structure may have changed.")
        else:
            print(f"[RADAR_SCRAPER_INFO] Successfully scraped {len(self.radar_data)} frames.")

    @staticmethod
    def _is_storm_pixel_array(img_array: np.ndarray) -> np.ndarray:
        """Return a boolean mask of pixels containing precipitation colors."""
        if img_array.ndim != 3:
            return np.zeros(img_array.shape[:2], dtype=bool)
        r, g, b = img_array[..., 0], img_array[..., 1], img_array[..., 2]
        
        # Non-rain masks
        dark_mask = np.maximum(np.maximum(r, g), b) < 50
        light_mask = np.minimum(np.minimum(r, g), b) > 240
        gray_mask = ((np.abs(r - g) < 20) & (np.abs(r - b) < 20) & (r >= 80) & (r <= 240))

        # Rain masks based on Meteocat legend
        # Light (feble)
        cyan_mask = (b > r + 30) & (b > g + 10) & (b > 120) & (g > r)
        # Note: purple is covered by magenta_mask logic but classified as light rain if not heavy.
        # This is handled in get_pixel_intensity. For detecting any rain, we include it.
        
        # Moderate (moderada)
        green_mask = (g > r + 30) & (g > b + 30) & (g > 100)
        yellow_mask = (r > 120) & (g > 120) & (b < 80)
        
        # Heavy (forta/calamarsa)
        orange_mask = (r > 180) & (g >= 80) & (g < 180) & (b < 80)
        red_mask = (r > 180) & (g < 80) & (b < 80)
        magenta_mask = (r > 120) & (g < 120) & (b > 120)

        return (cyan_mask | green_mask | yellow_mask | orange_mask | red_mask | magenta_mask) & \
               ~dark_mask & ~light_mask & ~gray_mask

    def create_composite_image(self) -> Tuple[Optional[Image.Image], List[str]]:
        """Combine all radar frames into a single composite image."""
        if not self.radar_data:
            return None, []

        composite = self.radar_data[0]['image'].copy()
        times = [self.radar_data[0]['time']]

        for frame_data in self.radar_data[1:]:
            frame = frame_data['image']
            times.append(frame_data['time'])
            comp_array = np.array(composite)
            frame_array = np.array(frame)
            new_storms = self._is_storm_pixel_array(frame_array) & ~self._is_storm_pixel_array(comp_array)
            composite_array = np.where(new_storms[..., None], frame_array, comp_array)
            composite = Image.fromarray(composite_array.astype(np.uint8))

        return composite, times

    # ------------------------- MAIN PROCESS -------------------------

    def process_frames(self, output_dir: str = "maps") -> Dict[str, bool]:
        """
        Analyze the radar composite for each user's route.
        Returns a dictionary with username as key and rain detection as value.
        """
        if not self.radar_data:
            print("No radar data. Call scrape_frames() first.")
            return {}
            
        os.makedirs(output_dir, exist_ok=True)
        self.last_composite, self.last_times = self.create_composite_image()
        
        if self.last_composite is None or not self.last_times:
            print("No frames available.")
            return {}
            
        results = {}

        width, height = self.last_composite.size
        timeframe = f"{self.last_times[0]} to {self.last_times[-1]}"
        print(f"Analyzing composite of {len(self.last_times)} frames: {timeframe}")
        
        for route in self.routes:
            try:
                user = route['user']
                x_home, y_home = self.latlon_to_pixels(*route['home'], (width, height))
                x_work, y_work = self.latlon_to_pixels(*route['work'], (width, height))

                # Get pixels and analyze intensity
                pixels = self.get_pixels_along_line(self.last_composite, x_home, y_home, x_work, y_work)
                intensities = [self.get_pixel_intensity(px) for px in pixels]
                
                # Calculate metrics
                rain_pixels = sum(1 for i in intensities if i > 0)
                valid_pixels = len(pixels)
                rain_ratio = rain_pixels / valid_pixels if valid_pixels > 0 else 0
                max_intensity = max(intensities) if intensities else 0
                
                # Determine rain status
                rain_detected = max_intensity > 0
                intensity_map = {0: "None", 1: "Light", 2: "Moderate", 3: "Heavy"}
                rain_intensity = intensity_map.get(max_intensity, "None")

                print(f"{rain_intensity} rain detected for {user} ({rain_pixels}/{valid_pixels} pixels, {rain_ratio:.1%})")
                results[user] = {
                    "will_rain": rain_detected,
                    "rain_intensity": rain_intensity,
                    "rain_ratio": rain_ratio,
                    "start_time": self.last_times[0] if self.last_times else None,
                    "end_time": self.last_times[-1] if self.last_times else None,
                }

                # Annotate and save the map
                self._save_annotated_map(user, x_home, y_home, x_work, y_work, timeframe, output_dir, rain_detected, rain_intensity)
                
            except Exception as e:
                print(f"Error processing route for {route.get('user', 'unknown')}: {str(e)}")
                results[route.get('user', 'unknown')] = {
                    "will_rain": False,
                    "rain_intensity": "None",
                    "rain_ratio": 0,
                    "start_time": self.last_times[0] if self.last_times else None,
                    "end_time": self.last_times[-1] if self.last_times else None,
                }

        return results
        
    def _save_annotated_map(self, user, x_home, y_home, x_work, y_work, timeframe, output_dir, rain_detected, rain_intensity):
        """Helper method to save annotated map with rain information."""
        annotated_img = self.last_composite.copy()
        draw = ImageDraw.Draw(annotated_img)
        
        # Draw route and markers
        shadow = 2
        draw.text((x_home + shadow, y_home + shadow), "🏠", font=self.emoji_font, fill="black", anchor="mm")
        draw.text((x_home, y_home), "🏠", font=self.emoji_font, fill="orange", anchor="mm")
        draw.text((x_work + shadow, y_work + shadow), "🏢", font=self.emoji_font, fill="black", anchor="mm")
        draw.text((x_work, y_work), "🏢", font=self.emoji_font, fill="orange", anchor="mm")
        
        # Draw route line with color based on rain detection
        line_color = "red" if rain_detected else "green"
        draw.line([(x_home, y_home), (x_work, y_work)], fill=line_color, width=3)
        
        # Add title with rain information
        status = f"{rain_intensity} rain detected" if rain_detected else "No significant rain"
        title = f"{user} — {timeframe} — {status}"
        
        # Draw title background
        tbbox = draw.textbbox((0, 0), title, font=self.font)
        tw, th = tbbox[2] - tbbox[0], tbbox[3] - tbbox[1]
        tx, ty = (annotated_img.width - tw) // 2, 10
        draw.rectangle([tx - 8, ty - 4, tx + tw + 8, ty + th + 4], fill="black")
        
        # Draw title text
        draw.text((tx, ty), title, font=self.font, fill=line_color)
        
        # Save the image
        filename = os.path.join(output_dir, f"{user}_map.png")
        annotated_img.save(filename)
        print(f"Saved map for {user} to {filename}")

    def close(self):
        """Close the Selenium WebDriver and clean up resources."""
        self.driver.quit()
