"""API Budget Tracker — ensures we stay within Eximpedia rate limits.

Eximpedia plan constraints:
- 100 API calls/day (each page request = 1 call)
- 3,000,000 total credits
- Data refreshes with ~2 week lag from customs

Budget allocation strategy:
- 60 calls/day for scheduled harvests (startup + background refresh)
- 40 calls/day reserved for on-demand searches (counterparty, ad-hoc commodity)
"""

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class APIBudgetTracker:
    """Singleton tracker for Eximpedia API usage."""

    _instance = None

    DAILY_LIMIT = 100
    HARVEST_BUDGET = 60   # calls reserved for scheduled harvests
    SEARCH_BUDGET = 40    # calls reserved for on-demand searches

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._calls_today = 0
        self._harvest_calls_today = 0
        self._search_calls_today = 0
        self._day_key = self._current_day_key()
        self._total_credits_consumed = 0
        self._total_credits_allotted = 3_000_000
        self._initialized = True

    def _current_day_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _maybe_reset(self):
        """Reset counters if a new UTC day has started."""
        key = self._current_day_key()
        if key != self._day_key:
            logger.info(
                f"New day ({key}). Resetting API budget. "
                f"Yesterday: {self._calls_today} calls used."
            )
            self._calls_today = 0
            self._harvest_calls_today = 0
            self._search_calls_today = 0
            self._day_key = key

    def record_call(self, call_type: str = "harvest"):
        """Record an API call."""
        self._maybe_reset()
        self._calls_today += 1
        if call_type == "harvest":
            self._harvest_calls_today += 1
        else:
            self._search_calls_today += 1

    def can_harvest(self) -> bool:
        """Check if there's budget for a harvest call."""
        self._maybe_reset()
        return self._harvest_calls_today < self.HARVEST_BUDGET

    def can_search(self) -> bool:
        """Check if there's budget for an on-demand search call."""
        self._maybe_reset()
        return self._search_calls_today < self.SEARCH_BUDGET

    def update_from_token(self, plan_constraints: dict):
        """Update credit tracking from JWT token payload."""
        credits = plan_constraints.get("credit_points", {})
        self._total_credits_consumed = credits.get("total_consumed_credits", 0)
        self._total_credits_allotted = credits.get("total_alloted_credits", 3_000_000)
        daily = plan_constraints.get("daily_limit_api", {})
        consumed = daily.get("consumed_daily_limit_api", 0)
        if consumed > self._calls_today:
            self._calls_today = consumed

    @property
    def status(self) -> dict:
        self._maybe_reset()
        return {
            "daily_calls_used": self._calls_today,
            "daily_calls_limit": self.DAILY_LIMIT,
            "harvest_calls_used": self._harvest_calls_today,
            "harvest_budget": self.HARVEST_BUDGET,
            "search_calls_used": self._search_calls_today,
            "search_budget": self.SEARCH_BUDGET,
            "daily_calls_remaining": max(0, self.DAILY_LIMIT - self._calls_today),
            "credits_consumed": self._total_credits_consumed,
            "credits_remaining": max(0, self._total_credits_allotted - self._total_credits_consumed),
            "day": self._day_key,
        }
