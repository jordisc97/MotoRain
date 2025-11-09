import asyncio
import logging
from typing import Dict

import requests

from constants import BACKEND_API_URL

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

    def _make_request():
        """Synchronous function to make the API request."""
        try:
            response = requests.post(BACKEND_API_URL, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            # Re-raise as a generic exception to be caught by the handler
            raise Exception(f"Failed to connect to backend API: {e}") from e

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


async def trigger_scrape_api():
    """Asynchronously calls the backend API to trigger a new scrape cycle."""
    scrape_url = BACKEND_API_URL.replace("check_rain/", "scrape/")

    def _make_request():
        """Synchronous function to make the API request."""
        try:
            # This is a 'fire and forget' request, so we use a short timeout.
            response = requests.post(scrape_url, timeout=10)
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