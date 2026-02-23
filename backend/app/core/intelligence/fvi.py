"""Flow Velocity Index (FVI) — measures acceleration/deceleration of trade.

FVI > 1.0 = flows accelerating vs. 30 days ago (bullish for demand or supply rush)
FVI < 1.0 = flows decelerating (supply shortage or demand pullback)

This is a leading indicator — flow changes precede price changes.
"""

from datetime import date, timedelta
from typing import Any

from app.data.reference_tables import SEASONAL_PATTERNS


class FlowVelocityIndex:
    """Compute flow velocity for commodity corridors."""

    def compute(
        self,
        records: list[dict],
        target_date: date | None = None,
        recent_window: int = 7,
        baseline_offset: int = 30,
    ) -> dict[str, Any]:
        """Compute FVI comparing recent volume to a baseline period.

        FVI = Volume(recent_window) / Volume(baseline_window of same length, offset days ago)

        Args:
            records: Normalized records with trade_date and quantity_mt
            target_date: Reference date
            recent_window: Days in recent window
            baseline_offset: How many days back the baseline starts
        """
        if not records:
            return self._empty()

        if target_date is None:
            target_date = date.today()

        recent_start = target_date - timedelta(days=recent_window)
        recent_end = target_date

        baseline_end = target_date - timedelta(days=baseline_offset)
        baseline_start = baseline_end - timedelta(days=recent_window)

        recent_vol = self._sum_volume(records, recent_start, recent_end)
        baseline_vol = self._sum_volume(records, baseline_start, baseline_end)

        if baseline_vol <= 0:
            fvi_raw = None
            signal = "NO_BASELINE"
        else:
            fvi_raw = round(recent_vol / baseline_vol, 4)
            signal = self._interpret(fvi_raw)

        return {
            "fvi_raw": fvi_raw,
            "signal": signal,
            "volume_recent_mt": round(recent_vol, 2),
            "volume_baseline_mt": round(baseline_vol, 2),
            "recent_window": f"{recent_start.isoformat()} to {recent_end.isoformat()}",
            "baseline_window": f"{baseline_start.isoformat()} to {baseline_end.isoformat()}",
            "n_records_recent": self._count_records(records, recent_start, recent_end),
            "n_records_baseline": self._count_records(records, baseline_start, baseline_end),
        }

    def compute_seasonally_adjusted(
        self,
        records: list[dict],
        hct_id: str,
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """Compute FVI adjusted for seasonal patterns.

        Divides raw FVI by the expected seasonal ratio to filter out
        normal seasonal acceleration/deceleration.
        """
        raw_result = self.compute(records, target_date)

        if raw_result["fvi_raw"] is None:
            return {**raw_result, "fvi_adjusted": None, "seasonal_factor": None}

        seasonal = SEASONAL_PATTERNS.get(hct_id)
        if not seasonal or "monthly_weights" not in seasonal:
            return {**raw_result, "fvi_adjusted": raw_result["fvi_raw"], "seasonal_factor": 1.0}

        target = target_date or date.today()
        current_month = target.month
        baseline_month = (target - timedelta(days=30)).month

        weights = seasonal["monthly_weights"]
        current_weight = weights.get(current_month, 1 / 12)
        baseline_weight = weights.get(baseline_month, 1 / 12)

        if baseline_weight <= 0:
            seasonal_factor = 1.0
        else:
            seasonal_factor = current_weight / baseline_weight

        fvi_adjusted = round(raw_result["fvi_raw"] / seasonal_factor, 4) if seasonal_factor > 0 else None
        adj_signal = self._interpret(fvi_adjusted) if fvi_adjusted else "UNKNOWN"

        return {
            **raw_result,
            "fvi_adjusted": fvi_adjusted,
            "seasonal_factor": round(seasonal_factor, 4),
            "signal_adjusted": adj_signal,
        }

    def compute_time_series(
        self,
        records: list[dict],
        start_date: date,
        end_date: date,
        hct_id: str | None = None,
    ) -> list[dict]:
        """Compute FVI for every day in a range."""
        series = []
        current = start_date
        while current <= end_date:
            if hct_id:
                point = self.compute_seasonally_adjusted(records, hct_id, current)
            else:
                point = self.compute(records, current)
            point["date"] = current.isoformat()
            series.append(point)
            current += timedelta(days=1)
        return series

    def _sum_volume(self, records: list[dict], start: date, end: date) -> float:
        total = 0.0
        for r in records:
            rd = self._parse_date(r.get("trade_date"))
            if rd and start <= rd <= end:
                qty = r.get("quantity_mt")
                if qty and qty > 0:
                    total += qty
        return total

    def _count_records(self, records: list[dict], start: date, end: date) -> int:
        count = 0
        for r in records:
            rd = self._parse_date(r.get("trade_date"))
            if rd and start <= rd <= end:
                count += 1
        return count

    @staticmethod
    def _interpret(fvi: float | None) -> str:
        if fvi is None:
            return "UNKNOWN"
        if fvi > 1.30:
            return "STRONG_ACCELERATION"
        if fvi > 1.10:
            return "MODERATE_ACCELERATION"
        if fvi >= 0.90:
            return "NORMAL"
        if fvi >= 0.70:
            return "MODERATE_DECELERATION"
        return "SEVERE_DECELERATION"

    @staticmethod
    def _parse_date(d) -> date | None:
        if d is None:
            return None
        if isinstance(d, date):
            return d
        try:
            return date.fromisoformat(str(d)[:10])
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _empty():
        return {
            "fvi_raw": None, "signal": "NO_DATA",
            "volume_recent_mt": 0, "volume_baseline_mt": 0,
            "recent_window": None, "baseline_window": None,
            "n_records_recent": 0, "n_records_baseline": 0,
        }
