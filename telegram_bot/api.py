import asyncio
import logging
from typing import Dict

import requests

from constants import BACKEND_BASE_URL

logger = logging.getLogger(__name__)


async def check_rain_api(user: str, home: str, work: str) -> Dict:
    """
    Asynchronously calls the backend API to check rain conditions.

    This function runs the synchronous `requests.post` call in a separate
    thread to avoid blocking the bot's main asyncio event loop.
    """
    payload = {
        "user": user,
        "home": home,
        "work": work,
    }
    headers = {"Content-Type": "application/json"}

    def _make_request():
        """Synchronous function to make the API request."""
        url = f"{BACKEND_BASE_URL}/check_rain/"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except ValueError:
                    error_detail = response.text
                return {"status": "error", "code": response.status_code, "error": error_detail}
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request to check_rain failed: {e}")
            return {"status": "error", "error": f"Failed to connect to backend API: {e}"}

    try:
        # Get the current running event loop
        loop = asyncio.get_running_loop()
        # Run the synchronous blocking call in a thread pool
        result = await loop.run_in_executor(None, _make_request)
        return result
    except Exception as e:
        logger.error(f"Error in API executor: {e}")
        # Ensure any exception is propagated
        raise


async def geocode_address_api(address: str) -> Dict:
    """Asynchronously calls the backend API to geocode and validate an address."""
    payload = {"address": address}
    headers = {"Content-Type": "application/json"}

    def _make_request():
        """Synchronous function to make the API request."""
        url = f"{BACKEND_BASE_URL}/geocode/"
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except (ValueError, AttributeError):
                    error_detail = response.text
                return {"status": "error", "code": response.status_code, "error": error_detail}
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request to geocode failed: {e}")
            return {"status": "error", "error": f"Failed to connect to backend API: {e}"}

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _make_request)
        return result
    except Exception as e:
        logger.error(f"Error in geocode_address_api executor: {e}")
        raise


async def trigger_scrape_api():
    """Asynchronously calls the backend API to trigger a new scrape cycle."""

    def _make_request():
        """Synchronous function to make the API request."""
        try:
            scrape_url = f"{BACKEND_BASE_URL}/scrape/"
            headers = {"Content-Type": "application/json"}
            # This is a 'fire and forget' request, so we use a short timeout.
            response = requests.post(scrape_url, headers=headers, timeout=10)
            if response.status_code == 202:
                logger.info(f"Backend accepted scrape request via {scrape_url}")
            else:
                logger.warning(
                    f"Backend returned status {response.status_code} for scrape request."
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"API request to trigger scrape failed: {e}")

    try:
        loop = asyncio.get_running_loop()
        # Run in an executor to avoid blocking the bot's event loop
        await loop.run_in_executor(None, _make_request)
    except Exception as e:
        logger.error(f"Error in trigger_scrape_api executor: {e}")