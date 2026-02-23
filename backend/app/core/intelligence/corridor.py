"""Corridor Analyzer — compare origins, compute FAB, and find arbitrage.

This module answers the trader's core questions:
- Which origin is cheapest right now?
- What's the delivered cost to my destination?
- Is there a basis play between corridors?
"""

from datetime import date
from typing import Any

from app.data.reference_tables import lookup_freight, calc_insurance, lookup_port_charges
from .ipc import ImpliedPriceCurve


class CorridorAnalyzer:
    """Compare corridors and compute freight-adjusted basis."""

    def __init__(self):
        self.ipc_engine = ImpliedPriceCurve()

    def compute_fab(
        self,
        records: list[dict],
        origin_country: str,
        origin_port: str,
        dest_port: str,
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """Compute Freight-Adjusted Basis for a corridor.

        FAB = FOB(origin) + Freight + Insurance + Port Charges = Implied CIF(dest)
        """
        # Filter records for this origin
        origin_records = [
            r for r in records
            if (r.get("origin_country") or "").upper() == origin_country.upper()
        ]

        ipc = self.ipc_engine.compute(origin_records, target_date)

        fob_price = ipc["price_usd_per_mt"]
        if fob_price is None:
            return {
                "origin": origin_country,
                "origin_port": origin_port,
                "dest_port": dest_port,
                "fob_usd_per_mt": None,
                "freight_usd_per_mt": None,
                "insurance_usd_per_mt": None,
                "port_charges_usd_per_mt": None,
                "implied_cif_usd_per_mt": None,
                "ipc_confidence": ipc["confidence"],
                "note": "Insufficient price data",
            }

        freight = lookup_freight(origin_port, dest_port) or 0
        insurance = fob_price * 0.0015  # Standard rate
        port_charges = lookup_port_charges(dest_port)

        implied_cif = fob_price + freight + insurance + port_charges

        return {
            "origin": origin_country,
            "origin_port": origin_port,
            "dest_port": dest_port,
            "fob_usd_per_mt": round(fob_price, 2),
            "freight_usd_per_mt": round(freight, 2),
            "insurance_usd_per_mt": round(insurance, 2),
            "port_charges_usd_per_mt": round(port_charges, 2),
            "implied_cif_usd_per_mt": round(implied_cif, 2),
            "ipc_confidence": ipc["confidence"],
            "ipc_n_records": ipc["n_records"],
        }

    def compare_origins(
        self,
        records: list[dict],
        origins: list[dict],
        dest_port: str,
        target_date: date | None = None,
    ) -> dict[str, Any]:
        """Compare multiple origins delivering to the same destination.

        Args:
            records: All normalized records for the commodity
            origins: List of dicts with 'country' and 'port' keys
            dest_port: Common destination port
        """
        comparisons = []
        for origin in origins:
            fab = self.compute_fab(
                records,
                origin["country"],
                origin["port"],
                dest_port,
                target_date,
            )
            comparisons.append(fab)

        # Sort by implied CIF (cheapest first)
        valid = [c for c in comparisons if c["implied_cif_usd_per_mt"] is not None]
        valid.sort(key=lambda x: x["implied_cif_usd_per_mt"])

        cheapest = valid[0] if valid else None
        most_expensive = valid[-1] if valid else None
        spread = None
        if cheapest and most_expensive:
            spread = round(
                most_expensive["implied_cif_usd_per_mt"] - cheapest["implied_cif_usd_per_mt"], 2
            )

        return {
            "destination_port": dest_port,
            "comparisons": comparisons,
            "cheapest_origin": cheapest["origin"] if cheapest else None,
            "origin_spread_usd": spread,
            "n_origins_with_data": len(valid),
        }

    def find_arbitrage(
        self,
        records: list[dict],
        corridors: list[dict],
        target_date: date | None = None,
    ) -> list[dict]:
        """Scan for arbitrage opportunities across corridors.

        An arb exists when the same commodity is cheaper from origin A
        but the market is buying from origin B (likely due to
        relationships, habit, or information lag).
        """
        # Compute FOB for each origin
        origin_prices: dict[str, dict] = {}
        for corridor in corridors:
            origin = corridor.get("origin_country", "")
            origin_recs = [
                r for r in records
                if (r.get("origin_country") or "").upper() == origin.upper()
            ]
            ipc = self.ipc_engine.compute(origin_recs, target_date)
            if ipc["price_usd_per_mt"] is not None:
                origin_prices[origin] = {
                    "fob": ipc["price_usd_per_mt"],
                    "confidence": ipc["confidence"],
                    "volume": ipc["volume_mt"],
                }

        arb_opportunities = []
        origins = list(origin_prices.keys())

        for i in range(len(origins)):
            for j in range(i + 1, len(origins)):
                a, b = origins[i], origins[j]
                pa, pb = origin_prices[a]["fob"], origin_prices[b]["fob"]
                spread = abs(pa - pb)
                spread_pct = spread / min(pa, pb) * 100

                if spread_pct > 3:  # Minimum threshold for meaningful arb
                    cheaper = a if pa < pb else b
                    expensive = b if pa < pb else a
                    arb_opportunities.append({
                        "cheaper_origin": cheaper,
                        "expensive_origin": expensive,
                        "cheaper_fob": round(min(pa, pb), 2),
                        "expensive_fob": round(max(pa, pb), 2),
                        "spread_usd": round(spread, 2),
                        "spread_pct": round(spread_pct, 1),
                        "confidence": min(
                            origin_prices[a]["confidence"],
                            origin_prices[b]["confidence"],
                            key=lambda x: {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}.get(x, 0),
                        ),
                    })

        return sorted(arb_opportunities, key=lambda x: x["spread_pct"], reverse=True)
