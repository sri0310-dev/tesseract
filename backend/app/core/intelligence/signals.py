"""Signal Generator — translates analytics into actionable trading alerts.

This is what the trader sees first. Every signal should be:
- Immediately understandable
- Quantified (numbers, not vague statements)
- Actionable (implies a position decision)
"""

from datetime import date, timedelta
from typing import Any


class SignalGenerator:
    """Generate trading signals from intelligence layer outputs."""

    def generate_from_fvi(self, fvi_result: dict, corridor_name: str) -> dict | None:
        """Generate signal from Flow Velocity Index."""
        fvi = fvi_result.get("fvi_adjusted") or fvi_result.get("fvi_raw")
        signal_type = fvi_result.get("signal_adjusted") or fvi_result.get("signal")

        if signal_type in ("NORMAL", "NO_DATA", "NO_BASELINE", "UNKNOWN"):
            return None

        severity_map = {
            "STRONG_ACCELERATION": "HIGH",
            "MODERATE_ACCELERATION": "MEDIUM",
            "MODERATE_DECELERATION": "MEDIUM",
            "SEVERE_DECELERATION": "HIGH",
        }
        severity = severity_map.get(signal_type, "LOW")

        vol_recent = fvi_result.get("volume_recent_mt", 0)
        vol_baseline = fvi_result.get("volume_baseline_mt", 0)
        change_pct = round((fvi - 1.0) * 100, 1) if fvi else 0

        if "ACCELERATION" in signal_type:
            direction = "up"
            headline = (
                f"{corridor_name}: flows UP {abs(change_pct)}% vs 30d ago "
                f"({vol_recent:.0f} MT recent vs {vol_baseline:.0f} MT baseline)"
            )
            implication = "Demand surge or supply rush. Potential price support."
        else:
            direction = "down"
            headline = (
                f"{corridor_name}: flows DOWN {abs(change_pct)}% vs 30d ago "
                f"({vol_recent:.0f} MT recent vs {vol_baseline:.0f} MT baseline)"
            )
            implication = "Demand pullback or supply shortage. Watch for price pressure."

        return {
            "signal_type": "FLOW_VELOCITY",
            "severity": severity,
            "headline": headline,
            "detail": {
                "corridor": corridor_name,
                "fvi": fvi,
                "direction": direction,
                "change_pct": change_pct,
                "implication": implication,
            },
        }

    def generate_from_sd_delta(self, sd_result: dict, commodity_name: str) -> dict | None:
        """Generate signal from S&D delta."""
        signal = sd_result.get("signal")
        if signal == "ON_TRACK":
            return None

        severity_map = {
            "OVER_SHIPPING": "MEDIUM",
            "UNDER_SHIPPING": "HIGH",
            "SLIGHTLY_OVER": "LOW",
            "SLIGHTLY_UNDER": "MEDIUM",
        }
        severity = severity_map.get(signal, "LOW")

        delta_pct = sd_result.get("delta_pct", 0)
        actual = sd_result.get("actual_cumulative_mt", 0)
        expected = sd_result.get("expected_cumulative_mt", 0)

        headline = (
            f"{commodity_name}: cumulative flow {abs(delta_pct):.1f}% "
            f"{'above' if delta_pct > 0 else 'below'} consensus "
            f"({actual:.0f} MT actual vs {expected:.0f} MT expected)"
        )

        return {
            "signal_type": "SD_DELTA",
            "severity": severity,
            "headline": headline,
            "detail": {
                "commodity": commodity_name,
                "delta_pct": delta_pct,
                "signal": signal,
                "implication": sd_result.get("implication", ""),
            },
        }

    def generate_from_ipc_change(
        self,
        current_ipc: dict,
        previous_ipc: dict,
        commodity_name: str,
        origin: str,
    ) -> dict | None:
        """Generate signal from IPC price movement."""
        curr_price = current_ipc.get("price_usd_per_mt")
        prev_price = previous_ipc.get("price_usd_per_mt")

        if curr_price is None or prev_price is None or prev_price == 0:
            return None

        change_pct = (curr_price - prev_price) / prev_price * 100
        if abs(change_pct) < 2.0:
            return None

        severity = "HIGH" if abs(change_pct) > 5 else "MEDIUM"
        direction = "up" if change_pct > 0 else "down"

        headline = (
            f"{commodity_name} from {origin}: implied FOB "
            f"{'↑' if change_pct > 0 else '↓'} {abs(change_pct):.1f}% "
            f"to ${curr_price:,.0f}/MT"
        )

        return {
            "signal_type": "PRICE_MOVEMENT",
            "severity": severity,
            "headline": headline,
            "detail": {
                "commodity": commodity_name,
                "origin": origin,
                "current_price": curr_price,
                "previous_price": prev_price,
                "change_pct": round(change_pct, 1),
                "direction": direction,
                "confidence": current_ipc.get("confidence"),
            },
        }

    def generate_from_counterparty(self, anomaly: dict) -> dict:
        """Generate signal from counterparty anomaly."""
        return {
            "signal_type": f"COUNTERPARTY_{anomaly['type']}",
            "severity": anomaly.get("severity", "MEDIUM"),
            "headline": anomaly["detail"],
            "detail": anomaly,
        }
