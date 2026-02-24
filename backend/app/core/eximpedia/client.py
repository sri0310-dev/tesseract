import asyncio
import time
import logging
from typing import Any

import httpx

from app.config import settings
from .token_manager import EximpediaTokenManager

logger = logging.getLogger(__name__)


class EximpediaAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Eximpedia API error {status_code}: {message}")


class EximpediaClient:
    """Rate-limited, paginated client for the Eximpedia Trade API.

    Handles:
    - Automatic token refresh via TokenManager
    - Concurrency limiting (semaphore)
    - Minimum interval between requests
    - Automatic pagination for full data extraction
    - Retry with exponential backoff on transient failures
    """

    def __init__(self, token_manager: EximpediaTokenManager | None = None):
        self.token_manager = token_manager or EximpediaTokenManager()
        self.base_url = settings.EXIMPEDIA_BASE_URL
        self.semaphore = asyncio.Semaphore(settings.API_MAX_CONCURRENT_REQUESTS)
        self.last_request_time: float = 0
        self.min_interval = settings.API_MIN_REQUEST_INTERVAL

    async def trade_shipment(self, payload: dict) -> dict:
        """Fetch a single page of trade shipment records."""
        return await self._request("/trade/shipment", payload)

    async def trade_shipment_all(self, payload: dict) -> list[dict]:
        """Fetch ALL pages of trade shipment records for a query.

        Automatically paginates through the full result set.
        Returns a flat list of all records.
        """
        all_records: list[dict] = []
        page = 1
        total_expected = None

        while True:
            payload["page_no"] = page
            payload["page_size"] = settings.API_PAGE_SIZE

            response = await self.trade_shipment(payload)

            records = response.get("data", [])
            if total_expected is None:
                # Eximpedia uses 'total_search_records' not 'total_records'
                total_expected = (
                    response.get("total_search_records")
                    or response.get("total_response_records")
                    or response.get("total_records")
                    or 0
                )

            all_records.extend(records)

            logger.info(
                f"Page {page}: fetched {len(records)} records "
                f"({len(all_records)}/{total_expected} total)"
            )

            if len(all_records) >= total_expected or len(records) == 0:
                break

            page += 1

        return all_records

    async def importer_summary(self, payload: dict) -> dict:
        return await self._request("/importer/summary", payload)

    async def exporter_summary(self, payload: dict) -> dict:
        return await self._request("/exporter/summary", payload)

    async def _request(self, endpoint: str, payload: dict) -> dict[str, Any]:
        """Make a rate-limited, authenticated API request with retry logic."""
        async with self.semaphore:
            # Enforce minimum interval
            now = time.time()
            wait = self.min_interval - (now - self.last_request_time)
            if wait > 0:
                await asyncio.sleep(wait)

            token = await self.token_manager.get_token()

            for attempt in range(4):
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{self.base_url}{endpoint}",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {token}",
                            },
                            json=payload,
                        )
                        self.last_request_time = time.time()

                        if response.status_code == 401:
                            # Token expired mid-flight — refresh and retry
                            self.token_manager.invalidate()
                            token = await self.token_manager.get_token()
                            continue

                        if response.status_code == 429:
                            # Rate limited — back off and retry
                            backoff = 2 ** (attempt + 2)  # 4s, 8s, 16s, 32s
                            logger.warning(
                                f"Rate limited on {endpoint} (attempt {attempt + 1}). "
                                f"Waiting {backoff}s"
                            )
                            await asyncio.sleep(backoff)
                            continue

                        if response.status_code != 200:
                            raise EximpediaAPIError(
                                response.status_code, response.text
                            )

                        return response.json()

                except httpx.HTTPError as e:
                    backoff = 2 ** (attempt + 1)
                    logger.warning(
                        f"Request to {endpoint} failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {backoff}s"
                    )
                    if attempt < 3:
                        await asyncio.sleep(backoff)
                    else:
                        raise

            raise EximpediaAPIError(0, "Exhausted all retry attempts")
