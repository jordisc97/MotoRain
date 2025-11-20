# --- Standard Library Imports ---
import os
import re
import time
from io import BytesIO
from typing import Dict, List, Optional, Tuple

# --- Third-Party Imports ---
import numpy as np
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- Constants ---
# Bounding box for Catalonia, Spain (min_latitude, min_longitude, max_latitude, max_longitude)
CATALUNYA_BOUNDS = (40.67, 0.14, 42.95, 3.5)


# --- Global Geocoder Setup ---
geolocator = Nominatim(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)
geocode_with_delay = RateLimiter(geolocator.geocode, min_delay_seconds=2, max_retries=2)


class RadarRainChecker:
    """
    Scrapes Catalonia radar images, builds a composite, and checks for rain
    along commute routes for multiple users.
    """
    # --- Class Constants ---
    NO_RAIN = 0
    LIGHT_RAIN = 1
    MODERATE_RAIN = 2
    HEAVY_RAIN = 3
    
    RAIN_INTENSITY_MAP = {
        NO_RAIN: "None",
        LIGHT_RAIN: "Light",
        MODERATE_RAIN: "Moderate",
        HEAVY_RAIN: "Heavy"
    }

    def __init__(self, chromedriver_path: Optional[str] = None, map_bounds: Tuple[float, float, float, float] = CATALUNYA_BOUNDS, routes: Optional[List[Dict]] = None, headless: bool = True):
        """
        Initializes the RadarRainChecker.

        Args:
            chromedriver_path (str, optional): Path to ChromeDriver. Defaults to None (auto-managed).
            map_bounds (Tuple[float, ...], optional): Map bounds (lat_min, lon_min, lat_max, lon_max). Defaults to CATALUNYA_BOUNDS.
            routes (List[Dict], optional): User routes with 'user', 'home', and 'work' coordinates. Defaults to None.
            headless (bool, optional): Whether to run Chrome in headless mode. Defaults to True.
        """
        self.map_bounds = map_bounds
        self.routes = routes if routes is not None else []
        self.headless = headless
        
        self.driver = self._initialize_webdriver(chromedriver_path)
        self.wait = WebDriverWait(self.driver, 20)
        
        self.radar_data: List[Dict] = []
        self.last_composite: Optional[Image.Image] = None
        self.last_times: List[str] = []

        self.font = self._load_font([("seguiemj.ttf", 28), ("arial.ttf", 24)])
        self.emoji_font = self._load_font([("seguiemj.ttf", 16), ("arial.ttf", 16)], fallback_font=self.font)

    # ------------------------- WEBDRIVER & FONT SETUP -------------------------

    def _initialize_webdriver(self, chromedriver_path: Optional[str]) -> webdriver.Chrome:
        """Sets up and returns a Chrome WebDriver instance."""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1200,1000")
        
        # Make the browser look less like a bot
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        if chromedriver_path:
            service = ChromeService(executable_path=chromedriver_path)
        else:
            service = ChromeService(ChromeDriverManager().install())
            
        return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _load_font(font_preferences: List[Tuple[str, int]], fallback_font: Optional[ImageFont.FreeTypeFont] = None) -> ImageFont.FreeTypeFont:
        """Loads a font from a list of preferences, with a fallback."""
        for font_name, size in font_preferences:
            try:
                return ImageFont.truetype(font_name, size)
            except OSError:
                continue
        if fallback_font:
            return fallback_font
        return ImageFont.load_default()

    # ------------------------- COORDINATE & PIXEL UTILITIES -------------------------

    @staticmethod
    def get_coordinates_from_address(address: str) -> Tuple[float, float]:
        """
        Convert an address string into geographic coordinates (latitude, longitude)
        using the Nominatim OpenStreetMap API, biased towards Catalonia.
        """
        if "catalonia" not in address.lower() and "catalunya" not in address.lower():
            query = f"{address}, Catalonia, Spain"
        else:
            query = address

        try:
            location = geocode_with_delay(
                query,
                viewbox=[(CATALUNYA_BOUNDS[0], CATALUNYA_BOUNDS[1]), (CATALUNYA_BOUNDS[2], CATALUNYA_BOUNDS[3])],
                bounded=True,
                timeout=10
            )
            if not location:
                raise ValueError(f"No coordinates found for address: {address}")
            return location.latitude, location.longitude
        except Exception as e:
            raise Exception(f"Error getting coordinates: {str(e)}")

    def latlon_to_pixels(self, lat: float, lon: float, img_size: Tuple[int, int]) -> Tuple[int, int]:
        """Convert latitude and longitude to pixel coordinates on the radar image."""
        lat_min, lon_min, lat_max, lon_max = self.map_bounds
        width, height = img_size
        x = (lon - lon_min) / (lon_max - lon_min) * width
        y = (lat_max - lat) / (lat_max - lat_min) * height
        return int(x), int(y)
        
    @staticmethod
    def is_within_bounds(coords: tuple, bounds: tuple) -> bool:
        """Check if a given (latitude, longitude) is within the specified bounds."""
        lat, lon = coords
        min_lat, min_lon, max_lat, max_lon = bounds
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon

    # ------------------------- RAIN DETECTION UTILITIES -------------------------

    @classmethod
    def get_pixel_intensity(cls, pixel: Tuple[int, int, int]) -> int:
        """
        Determine rain intensity from a pixel's color based on the Meteocat legend.

        Returns:
            int: An intensity level (0: No rain, 1: Light, 2: Moderate, 3: Heavy).
        """
        r, g, b = pixel[:3]

        # --- Non-rain colors (background, map features) ---
        is_dark_or_light = max(r, g, b) < 50 or min(r, g, b) > 240
        is_gray = (abs(r - g) < 20) and (abs(r - b) < 20) and (r >= 80) and (r <= 240)
        if is_dark_or_light or is_gray:
            return cls.NO_RAIN

        # --- Heavy rain (forta: oranges, reds) ---
        is_orange_or_red = (r > 180 and 80 <= g < 180 and b < 80) or \
                           (r > 180 and g < 80 and b < 80)
        if is_orange_or_red:
            return cls.HEAVY_RAIN

        # --- Moderate rain (moderada: greens, yellows, magentas) ---
        is_green = g > r + 30 and g > b + 30 and g > 100
        is_yellow = r > 120 and g > 120 and b < 80
        is_magenta = r > 120 and g < 120 and b > 120
        if is_green or is_yellow or is_magenta:
            return cls.MODERATE_RAIN

        # --- Light rain (feble: purples, blues, cyans) ---
        is_cyan_or_blue = b > r + 30 and b > g + 10 and b > 120 and g > r
        if is_cyan_or_blue:
            return cls.LIGHT_RAIN

        return cls.NO_RAIN

    @classmethod
    def is_rain_color(cls, rgb_pixel: Tuple[int, int, int]) -> bool:
        """Determine whether a pixel color indicates rain based on intensity."""
        return cls.get_pixel_intensity(rgb_pixel) > cls.NO_RAIN

    def contains_rain_color(self, pixels: List[Tuple[int, int, int]]) -> bool:
        """Check if a list of pixels contains a significant number of rain pixels."""
        rain_pixel_count = sum(1 for px in pixels if self.is_rain_color(px))
        # Require at least 2 pixels for longer routes to avoid false positives
        threshold = 2 if len(pixels) > 10 else 1
        return rain_pixel_count >= threshold

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

    # ------------------------- SCRAPE & COMPOSITE -------------------------

    def open_radar_page(self, url: str = "https://www.meteo.cat/observacions/radar") -> None:
        """Open the Catalonia radar webpage and handle cookie consent."""
        self.driver.get(url)
        try:
            accept_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Acceptar')]"))
            )
            accept_button.click()
            print("Accepted cookies.")
        except TimeoutException:
            print("Cookie consent button not found, proceeding.")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "adveccio_slider"))
        )

        try:
            print("Waiting for base map to load...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".leaflet-tile-container img"))
            )
            time.sleep(3)  # Allow a few seconds for all tiles to render
            print("Base map loaded.")
        except TimeoutException:
            print("Warning: Timed out waiting for map tiles. The map may be incomplete.")

    def scrape_frames(self) -> None:
        """Scrape all available radar frames from the webpage slider."""
        slider = self.driver.find_element(By.ID, "adveccio_slider")
        map_container = self.driver.find_element(By.ID, "map")
        min_val, max_val, step = int(slider.get_attribute("min")), int(slider.get_attribute("max")), int(slider.get_attribute("step"))

        self.radar_data = []
        for val in range(min_val, max_val + step, step):
            self.driver.execute_script(
                f"document.getElementById('adveccio_slider').value = {val};"
                "document.getElementById('adveccio_slider').dispatchEvent(new Event('input'));"
            )
            
            # This delay is crucial as the site's loading indicators are unreliable.
            time.sleep(1.5)
            
            time_text = self.driver.find_element(By.CLASS_NAME, "time_label").text.strip()
            
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
        """
        Return a boolean mask of pixels containing precipitation colors.
        This method is optimized for NumPy and used for creating the composite image.
        """
        if img_array.ndim != 3 or img_array.shape[2] < 3:
            return np.zeros(img_array.shape[:2], dtype=bool)
        r, g, b = img_array[..., 0], img_array[..., 1], img_array[..., 2]
        
        # --- Non-rain masks ---
        dark_mask = np.maximum(np.maximum(r, g), b) < 50
        light_mask = np.minimum(np.minimum(r, g), b) > 240
        gray_mask = ((np.abs(r.astype(int) - g.astype(int)) < 20) &
                     (np.abs(r.astype(int) - b.astype(int)) < 20) &
                     (r >= 80) & (r <= 240))

        # --- Rain masks (based on Meteocat legend) ---
        cyan_mask = (b > r + 30) & (b > g + 10) & (b > 120) & (g > r)
        green_mask = (g > r + 30) & (g > b + 30) & (g > 100)
        yellow_mask = (r > 120) & (g > 120) & (b < 80)
        orange_mask = (r > 180) & (g >= 80) & (g < 180) & (b < 80)
        red_mask = (r > 180) & (g < 80) & (b < 80)
        magenta_mask = (r > 120) & (g < 120) & (b > 120)

        rain_mask = (cyan_mask | green_mask | yellow_mask | orange_mask | red_mask | magenta_mask)
        non_rain_mask = dark_mask | light_mask | gray_mask

        return rain_mask & ~non_rain_mask

    def create_composite_image(self) -> Tuple[Optional[Image.Image], List[str]]:
        """Combine all scraped radar frames into a single composite image."""
        if not self.radar_data:
            return None, []

        base_image = self.radar_data[0]['image'].copy()
        times = [self.radar_data[0]['time']]
        
        comp_array = np.array(base_image)
        is_storm_base = self._is_storm_pixel_array(comp_array)

        for frame_data in self.radar_data[1:]:
            frame_image = frame_data['image']
            times.append(frame_data['time'])
            
            frame_array = np.array(frame_image)
            is_storm_frame = self._is_storm_pixel_array(frame_array)
            
            # Identify new storm pixels that were not in the base composite yet
            new_storm_mask = is_storm_frame & ~is_storm_base
            
            # Update the composite array and the storm base mask
            comp_array = np.where(new_storm_mask[..., None], frame_array, comp_array)
            is_storm_base |= new_storm_mask

        return Image.fromarray(comp_array.astype(np.uint8)), times

    # ------------------------- MAIN PROCESSING & ANALYSIS -------------------------

    def process_frames(self, output_dir: str = "maps") -> Dict[str, bool]:
        """
        Analyze the radar composite for each user's route and save annotated maps.

        Returns:
            Dict[str, bool]: A dictionary with username as key and rain detection results.
        """
        if not self.radar_data:
            print("No radar data available. Call scrape_frames() first.")
            return {}
            
        os.makedirs(output_dir, exist_ok=True)
        self.last_composite, self.last_times = self.create_composite_image()
        
        if self.last_composite is None or not self.last_times:
            print("Failed to create a composite image from frames.")
            return {}
            
        results = {}
        width, height = self.last_composite.size
        timeframe = f"{self.last_times[0]} to {self.last_times[-1]}"
        print(f"Analyzing composite of {len(self.last_times)} frames: {timeframe}")
        
        for route in self.routes:
            user = route.get('user', 'unknown')
            try:
                x_home, y_home = self.latlon_to_pixels(*route['home'], (width, height))
                x_work, y_work = self.latlon_to_pixels(*route['work'], (width, height))

                pixels = self.get_pixels_along_line(self.last_composite, x_home, y_home, x_work, y_work)
                intensities = [self.get_pixel_intensity(px) for px in pixels]
                
                rain_pixels = sum(1 for i in intensities if i > self.NO_RAIN)
                valid_pixels = len(pixels)
                rain_ratio = rain_pixels / valid_pixels if valid_pixels > 0 else 0
                max_intensity = max(intensities) if intensities else self.NO_RAIN
                
                rain_detected = max_intensity > self.NO_RAIN
                rain_intensity_str = self.RAIN_INTENSITY_MAP.get(max_intensity, "None")

                print(f"{rain_intensity_str} rain detected for {user} ({rain_pixels}/{valid_pixels} pixels, {rain_ratio:.1%})")
                results[user] = {
                    "will_rain": rain_detected,
                    "rain_intensity": rain_intensity_str,
                    "rain_ratio": rain_ratio,
                    "start_time": self.last_times[0],
                    "end_time": self.last_times[-1],
                }

                self._save_annotated_map(user, x_home, y_home, x_work, y_work, timeframe, output_dir, rain_detected, rain_intensity_str)
                
            except Exception as e:
                print(f"Error processing route for {user}: {str(e)}")
                results[user] = {
                    "will_rain": False,
                    "rain_intensity": "None",
                    "rain_ratio": 0,
                    "start_time": self.last_times[0] if self.last_times else None,
                    "end_time": self.last_times[-1] if self.last_times else None,
                }

        return results
        
    def _save_annotated_map(self, user: str, x_home: int, y_home: int, x_work: int, y_work: int, timeframe: str, output_dir: str, rain_detected: bool, rain_intensity: str):
        """Helper method to draw route information on a map and save it."""
        annotated_img = self.last_composite.copy()
        draw = ImageDraw.Draw(annotated_img)
        
        # --- Draw route and markers with shadows for better visibility ---
        shadow = 2
        line_color = "red" if rain_detected else "green"
        
        draw.text((x_home + shadow, y_home + shadow), "🏠", font=self.emoji_font, fill="black", anchor="mm")
        draw.text((x_home, y_home), "🏠", font=self.emoji_font, fill="orange", anchor="mm")
        draw.text((x_work + shadow, y_work + shadow), "🏢", font=self.emoji_font, fill="black", anchor="mm")
        draw.text((x_work, y_work), "🏢", font=self.emoji_font, fill="orange", anchor="mm")
        draw.line([(x_home, y_home), (x_work, y_work)], fill=line_color, width=3)
        
        # --- Draw title with a semi-transparent background ---
        status = f"{rain_intensity} rain detected" if rain_detected else "No significant rain"
        title = f"{user} — {timeframe} — {status}"
        
        tbbox = draw.textbbox((0, 0), title, font=self.font)
        tw, th = tbbox[2] - tbbox[0], tbbox[3] - tbbox[1]
        tx, ty = (annotated_img.width - tw) // 2, 10
        draw.rectangle([tx - 10, ty - 5, tx + tw + 10, ty + th + 5], fill="black")
        draw.text((tx, ty), title, font=self.font, fill=line_color)
        
        # --- Save the final image ---
        filename = os.path.join(output_dir, f"{user}_map.png")
        annotated_img.save(filename)
        print(f"Saved annotated map for {user} to {filename}")

    def close(self):
        """Close the Selenium WebDriver and clean up resources."""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()


if __name__ == '__main__':
    # --- EXAMPLE USAGE ---
    # This block will run when the script is executed directly.
    # It demonstrates how to use the RadarRainChecker to check rain for a predefined route.

    print("--- Starting MotoRain Radar Checker ---")

    # 1. Define sample routes for different users.
    # The coordinates (latitude, longitude) should be within Catalonia.
    sample_routes = [
        {
            "user": "Jordi",
            "home": (41.3851, 2.1734),  # Barcelona
            "work": (41.4036, 2.1744)   # Sagrada Familia
        },
        {
            "user": "Montserrat",
            "home": (41.5947, 1.8277),  # Manresa
            "work": (41.7247, 2.2513)   # Vic
        }
    ]

    # 2. Initialize the checker.
    # Using headless=False will open a visible Chrome window, which is useful for debugging.
    # Set headless=True for automated runs.
    checker = None
    try:
        checker = RadarRainChecker(routes=sample_routes, headless=True)
        
        # 3. Open the radar page and scrape the latest frames.
        print("\n[STEP 1] Opening radar page...")
        checker.open_radar_page()
        
        print("\n[STEP 2] Scraping radar frames...")
        checker.scrape_frames()
        
        # 4. Process the frames to check for rain and generate maps.
        print("\n[STEP 3] Processing frames and analyzing routes...")
        rain_results = checker.process_frames(output_dir="maps_output")
        
        # 5. Print the final results.
        print("\n--- Rain Check Results ---")
        if rain_results:
            for user, result in rain_results.items():
                status = "RAIN" if result['will_rain'] else "NO RAIN"
                intensity = f"({result['rain_intensity']})" if result['will_rain'] else ""
                print(f"  - {user}: {status} {intensity} forecast between {result['start_time']} and {result['end_time']}.")
        else:
            print("  No results were generated.")

    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
    finally:
        # 6. Ensure the browser is closed properly.
        if checker:
            print("\n--- Shutting down ---")
            checker.close()    