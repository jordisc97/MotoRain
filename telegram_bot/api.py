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
