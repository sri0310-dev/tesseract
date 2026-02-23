"""Supply-Demand Tracker — the killer signal.

Tracks cumulative exports/imports vs. consensus estimates.
The delta between what the market expects and what is actually
shipping is the highest-alpha signal in commodity trading.
"""

from datetime import date, timedelta
from typing import Any


class SupplyDemandTracker:
    """Compute implied supply-demand balance sheets and deltas."""

    def compute_cumulative_flows(
        self,
        records: list[dict],
        start_date: date,
        end_date: date,
        trade_type: str | None = None,
    ) -> dict[str, Any]:
        """Compute cumulative export/import volumes over a period.

        Groups by origin country to show source breakdown.
        """
        daily_volumes: dict[str, float] = {}
        country_volumes: dict[str, float] = {}
        total_value = 0.0
        total_volume = 0.0
        record_count = 0

        for r in records:
            rd = self._parse_date(r.get("trade_date"))
            if rd is None or rd < start_date or rd > end_date:
                continue
            if trade_type and r.get("trade_type") != trade_type.upper():
                continue

            qty = r.get("quantity_mt") or 0
            val = r.get("fob_usd_total") or 0

            if qty > 0:
                day_key = rd.isoformat()
                daily_volumes[day_key] = daily_volumes.get(day_key, 0) + qty

                origin = r.get("origin_country") or r.get("destination_country") or "UNKNOWN"
                country_volumes[origin] = country_volumes.get(origin, 0) + qty

                total_volume += qty
                total_value += val
                record_count += 1

        # Build cumulative series
        cumulative_series = []
        running = 0.0
        current = start_date
        while current <= end_date:
            day_key = current.isoformat()
            day_vol = daily_volumes.get(day_key, 0)
            running += day_vol
            cumulative_series.append({
                "date": day_key,
                "daily_volume_mt": round(day_vol, 2),
                "cumulative_volume_mt": round(running, 2),
            })
            current += timedelta(days=1)

        # Country breakdown sorted by volume
        breakdown = sorted(
            [{"country": k, "volume_mt": round(v, 2),
              "share_pct": round(v / total_volume * 100, 1) if total_volume > 0 else 0}
             for k, v in country_volumes.items()],
            key=lambda x: x["volume_mt"],
            reverse=True,
        )

        return {
            "total_volume_mt": round(total_volume, 2),
            "total_value_usd": round(total_value, 2),
            "record_count": record_count,
            "avg_price_per_mt": round(total_value / total_volume, 2) if total_volume > 0 else None,
            "country_breakdown": breakdown,
            "daily_series": cumulative_series,
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
        }

    def compute_sd_delta(
        self,
        records: list[dict],
        consensus_annual_mt: float,
        crop_year_start: date,
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """Compute deviation from consensus S&D estimate.

        The MOST valuable output: how much is actual trade flow
        above or below what the market expects at this point in time?

        Args:
            records: Normalized records
            consensus_annual_mt: USDA/FAO annual estimate in MT
            crop_year_start: Start of the crop year
            target_date: Date to evaluate
        """
        if target_date is None:
            target_date = date.today()

        crop_year_end = date(crop_year_start.year + 1, crop_year_start.month, crop_year_start.day)

        # Days elapsed and total in crop year
        days_elapsed = (target_date - crop_year_start).days
        days_total = (crop_year_end - crop_year_start).days
        progress_pct = days_elapsed / days_total if days_total > 0 else 0

        # Expected cumulative at this point (pro-rata)
        expected_cumulative = consensus_annual_mt * progress_pct

        # Actual cumulative from trade data
        flows = self.compute_cumulative_flows(records, crop_year_start, target_date)
        actual_cumulative = flows["total_volume_mt"]

        # The delta
        delta_mt = actual_cumulative - expected_cumulative
        delta_pct = (delta_mt / expected_cumulative * 100) if expected_cumulative > 0 else 0

        # Trading signal
        if delta_pct > 10:
            signal = "OVER_SHIPPING"
            implication = "Supply more ample than market expects. Bearish."
        elif delta_pct > 5:
            signal = "SLIGHTLY_OVER"
            implication = "Marginally above expectations. Watch for trend."
        elif delta_pct < -10:
            signal = "UNDER_SHIPPING"
            implication = "Supply tighter than market expects. Bullish."
        elif delta_pct < -5:
            signal = "SLIGHTLY_UNDER"
            implication = "Marginally below expectations. Watch for trend."
        else:
            signal = "ON_TRACK"
            implication = "Flows in line with consensus."

        return {
            "actual_cumulative_mt": round(actual_cumulative, 2),
            "expected_cumulative_mt": round(expected_cumulative, 2),
            "delta_mt": round(delta_mt, 2),
            "delta_pct": round(delta_pct, 1),
            "consensus_annual_mt": consensus_annual_mt,
            "crop_year_progress_pct": round(progress_pct * 100, 1),
            "signal": signal,
            "implication": implication,
            "country_breakdown": flows["country_breakdown"],
            "record_count": flows["record_count"],
        }

    def compute_yoy_comparison(
        self,
        current_records: list[dict],
        previous_records: list[dict],
        period_start: date,
        period_end: date,
    ) -> dict[str, Any]:
        """Compare current period flows against same period last year."""
        current = self.compute_cumulative_flows(current_records, period_start, period_end)

        prev_start = date(period_start.year - 1, period_start.month, period_start.day)
        prev_end = date(period_end.year - 1, period_end.month, period_end.day)
        previous = self.compute_cumulative_flows(previous_records, prev_start, prev_end)

        curr_vol = current["total_volume_mt"]
        prev_vol = previous["total_volume_mt"]
        yoy_change = ((curr_vol - prev_vol) / prev_vol * 100) if prev_vol > 0 else None

        return {
            "current_period": current,
            "previous_period": previous,
            "yoy_volume_change_pct": round(yoy_change, 1) if yoy_change is not None else None,
            "yoy_value_change_pct": (
                round((current["total_value_usd"] - previous["total_value_usd"])
                      / previous["total_value_usd"] * 100, 1)
                if previous["total_value_usd"] > 0 else None
            ),
        }

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
