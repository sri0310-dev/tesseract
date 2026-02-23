import asyncio
import time
import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EximpediaTokenManager:
    """Singleton token manager for Eximpedia API authentication.

    Handles OAuth2 token lifecycle — requests new tokens when needed and
    refreshes them 5 minutes before expiry to avoid mid-request failures.
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.client_id = settings.EXIMPEDIA_CLIENT_ID
        self.client_secret = settings.EXIMPEDIA_CLIENT_SECRET
        self.base_url = settings.EXIMPEDIA_BASE_URL
        self.token: str | None = None
        self.token_expiry: float = 0
        self._refresh_lock = asyncio.Lock()
        self._initialized = True

    async def get_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if self.token and time.time() < (self.token_expiry - settings.TOKEN_REFRESH_BUFFER_SECONDS):
            return self.token

        async with self._refresh_lock:
            # Double-check after acquiring lock
            if self.token and time.time() < (self.token_expiry - settings.TOKEN_REFRESH_BUFFER_SECONDS):
                return self.token

            return await self._refresh_token()

    async def _refresh_token(self) -> str:
        """Request a new token from the Eximpedia OAuth2 endpoint."""
        logger.info("Refreshing Eximpedia API token...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(3):
                try:
                    response = await client.post(
                        f"{self.base_url}/oauth2/token",
                        json={
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    self.token = data["AccessToken"]
                    self.token_expiry = time.time() + 3600
                    logger.info("Token refreshed successfully")
                    return self.token

                except (httpx.HTTPError, KeyError) as e:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Token refresh attempt {attempt + 1} failed: {e}. Retrying in {wait}s")
                    if attempt < 2:
                        await asyncio.sleep(wait)

        raise RuntimeError("Failed to refresh Eximpedia token after 3 attempts")

    def invalidate(self):
        """Force token refresh on next request."""
        self.token = None
        self.token_expiry = 0
