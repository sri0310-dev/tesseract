"""Implied Price Curve (IPC) — the continuous price discovery engine.

For commodities with NO published benchmark, this constructs a
volume-weighted median price from actual shipment records. This is
the single most valuable analytical output of the system.
"""

import statistics
from datetime import date, timedelta
from typing import Any


class ImpliedPriceCurve:
    """Compute implied daily prices from normalized trade records."""

    def compute(
        self,
        records: list[dict],
        target_date: date | None = None,
        window_days: int = 5,
        min_records_high: int = 20,
        min_records_medium: int = 5,
    ) -> dict[str, Any]:
        """Compute the IPC for a set of records on a given date.

        Uses a volume-weighted median over a rolling window.

        Args:
            records: Normalized trade records with fob_usd_per_mt and quantity_mt
            target_date: Date to compute IPC for (defaults to latest)
            window_days: Rolling window size in days
            min_records_high: Minimum records for HIGH confidence
            min_records_medium: Minimum records for MEDIUM confidence

        Returns dict with:
            price_usd_per_mt, confidence, n_records, volume_mt, price_iqr,
            price_min, price_max, window_start, window_end
        """
        if not records:
            return self._empty_result()

        if target_date is None:
            dates = [self._parse_date(r.get("trade_date")) for r in records]
            dates = [d for d in dates if d is not None]
            target_date = max(dates) if dates else date.today()

        window_start = target_date - timedelta(days=window_days)
        window_end = target_date

        # Filter records within window with valid prices
        window_records = []
        for r in records:
            rd = self._parse_date(r.get("trade_date"))
            price = r.get("fob_usd_per_mt")
            qty = r.get("quantity_mt")
            status = r.get("price_status", "NORMAL")

            if (rd and window_start <= rd <= window_end
                    and price and price > 0
                    and status == "NORMAL"):
                window_records.append({
                    "price": price,
                    "weight": qty if qty and qty > 0 else 1.0,
                })

        if not window_records:
            return self._empty_result(window_start, window_end)

        # Volume-weighted median
        prices = [r["price"] for r in window_records]
        weights = [r["weight"] for r in window_records]
        total_volume = sum(weights)

        wm_price = self._weighted_median(prices, weights)

        # Statistics
        n_records = len(window_records)
        sorted_prices = sorted(prices)
        q1_idx = max(0, len(sorted_prices) // 4 - 1)
        q3_idx = min(len(sorted_prices) - 1, 3 * len(sorted_prices) // 4)
        iqr = sorted_prices[q3_idx] - sorted_prices[q1_idx] if len(sorted_prices) > 1 else 0

        # Confidence scoring
        dispersion = iqr / wm_price if wm_price > 0 else 1.0
        if n_records >= min_records_high and dispersion < 0.15:
            confidence = "HIGH"
        elif n_records >= min_records_medium:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return {
            "price_usd_per_mt": round(wm_price, 2),
            "confidence": confidence,
            "n_records": n_records,
            "volume_mt": round(total_volume, 2),
            "price_iqr": round(iqr, 2),
            "price_min": round(min(prices), 2),
            "price_max": round(max(prices), 2),
            "price_mean": round(statistics.mean(prices), 2),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        }

    def compute_time_series(
        self,
        records: list[dict],
        start_date: date,
        end_date: date,
        window_days: int = 5,
    ) -> list[dict]:
        """Compute IPC for every day in a date range."""
        series = []
        current = start_date
        while current <= end_date:
            point = self.compute(records, current, window_days)
            point["date"] = current.isoformat()
            series.append(point)
            current += timedelta(days=1)
        return series

    @staticmethod
    def _weighted_median(values: list[float], weights: list[float]) -> float:
        """Compute the weighted median of a list of values."""
        if not values:
            return 0.0
        if len(values) == 1:
            return values[0]

        pairs = sorted(zip(values, weights))
        cumulative = 0
        total = sum(weights)
        half = total / 2

        for value, weight in pairs:
            cumulative += weight
            if cumulative >= half:
                return value

        return pairs[-1][0]

    @staticmethod
    def _parse_date(d: Any) -> date | None:
        if d is None:
            return None
        if isinstance(d, date):
            return d
        try:
            return date.fromisoformat(str(d)[:10])
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _empty_result(ws=None, we=None) -> dict:
        return {
            "price_usd_per_mt": None,
            "confidence": "NONE",
            "n_records": 0,
            "volume_mt": 0,
            "price_iqr": None,
            "price_min": None,
            "price_max": None,
            "price_mean": None,
            "window_start": ws.isoformat() if ws else None,
            "window_end": we.isoformat() if we else None,
        }
