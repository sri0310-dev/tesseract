"""Counterparty Intelligence — who is buying, who is selling, and why it matters.

Entity resolution, market share analysis, and anomaly detection on
the buyer/seller level. Detecting when a major player shifts behaviour
is one of the most powerful leading indicators in opaque markets.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Any


class CounterpartyIntelligence:
    """Analyze counterparty behaviour from normalized trade records."""

    # Known major entity aliases for entity resolution
    ENTITY_ALIASES: dict[str, list[str]] = {
        "Olam Group": [
            "OLAM", "OLAM INTERNATIONAL", "OLAM AGRI", "OLAM FOOD",
            "OLAM NIGERIA", "OLAM GHANA", "OLAM VIETNAM", "OLAM IVORY",
        ],
        "Louis Dreyfus": [
            "LOUIS DREYFUS", "LDC", "LD COMMODITIES",
        ],
        "Cargill": [
            "CARGILL", "CARGILL INC", "CARGILL INDIA", "CARGILL WEST AFRICA",
        ],
        "ADM": [
            "ARCHER DANIELS", "ADM", "A.D.M",
        ],
        "Bunge": [
            "BUNGE", "BUNGE LIMITED",
        ],
        "Wilmar": [
            "WILMAR", "WILMAR INTERNATIONAL",
        ],
    }

    def resolve_entity(self, name: str) -> str:
        """Resolve an entity name to its canonical form."""
        if not name:
            return "UNKNOWN"
        upper = name.upper().strip()
        for canonical, aliases in self.ENTITY_ALIASES.items():
            for alias in aliases:
                if alias in upper:
                    return canonical
        return name.strip()

    def compute_market_shares(
        self,
        records: list[dict],
        party_field: str = "consignee",
        start_date: date | None = None,
        end_date: date | None = None,
        top_n: int = 20,
    ) -> dict[str, Any]:
        """Compute market shares by volume for buyers or sellers.

        Args:
            records: Normalized records
            party_field: 'consignee' for buyers, 'consignor' for sellers
            start_date/end_date: Period filter
            top_n: Number of top entities to return
        """
        entity_volumes: dict[str, float] = defaultdict(float)
        entity_values: dict[str, float] = defaultdict(float)
        entity_shipments: dict[str, int] = defaultdict(int)
        total_volume = 0.0

        for r in records:
            rd = self._parse_date(r.get("trade_date"))
            if start_date and rd and rd < start_date:
                continue
            if end_date and rd and rd > end_date:
                continue

            entity = self.resolve_entity(r.get(party_field, ""))
            qty = r.get("quantity_mt") or 0
            val = r.get("fob_usd_total") or 0

            if qty > 0:
                entity_volumes[entity] += qty
                entity_values[entity] += val
                entity_shipments[entity] += 1
                total_volume += qty

        # Sort by volume and take top N
        sorted_entities = sorted(entity_volumes.items(), key=lambda x: x[1], reverse=True)
        top_entities = sorted_entities[:top_n]

        results = []
        for entity, vol in top_entities:
            results.append({
                "entity": entity,
                "volume_mt": round(vol, 2),
                "value_usd": round(entity_values[entity], 2),
                "shipments": entity_shipments[entity],
                "market_share_pct": round(vol / total_volume * 100, 1) if total_volume > 0 else 0,
                "avg_price_per_mt": (
                    round(entity_values[entity] / vol, 2) if vol > 0 else None
                ),
            })

        # HHI concentration index
        hhi = sum((e["market_share_pct"] / 100) ** 2 for e in results)

        return {
            "party_type": party_field,
            "total_volume_mt": round(total_volume, 2),
            "unique_entities": len(entity_volumes),
            "hhi": round(hhi, 4),
            "concentration": (
                "HIGH" if hhi > 0.25 else "MODERATE" if hhi > 0.15 else "LOW"
            ),
            "top_entities": results,
        }

    def detect_anomalies(
        self,
        current_records: list[dict],
        historical_records: list[dict],
        party_field: str = "consignee",
        lookback_months: int = 12,
    ) -> list[dict]:
        """Detect counterparty anomalies: new entrants, withdrawals, surges.

        Compares the current period against historical patterns to find
        entities that are behaving differently than usual.
        """
        today = date.today()
        current_start = today - timedelta(days=30)
        historical_start = today - timedelta(days=lookback_months * 30)

        current_shares = self.compute_market_shares(
            current_records, party_field, current_start, today
        )
        historical_shares = self.compute_market_shares(
            historical_records, party_field, historical_start, current_start
        )

        current_entities = {e["entity"]: e for e in current_shares["top_entities"]}
        historical_entities = {e["entity"]: e for e in historical_shares["top_entities"]}

        anomalies = []

        # New entrants (in current but not historical)
        for entity, data in current_entities.items():
            if entity not in historical_entities and data["volume_mt"] > 0:
                anomalies.append({
                    "type": "NEW_ENTRANT",
                    "entity": entity,
                    "severity": "HIGH" if data["market_share_pct"] > 5 else "MEDIUM",
                    "detail": (
                        f"New {party_field} detected: {entity} with "
                        f"{data['volume_mt']} MT ({data['shipments']} shipments)"
                    ),
                    "volume_mt": data["volume_mt"],
                    "market_share_pct": data["market_share_pct"],
                })

        # Withdrawals (in historical but not current)
        for entity, hist in historical_entities.items():
            if entity not in current_entities and hist["market_share_pct"] > 3:
                anomalies.append({
                    "type": "WITHDRAWAL",
                    "entity": entity,
                    "severity": "HIGH" if hist["market_share_pct"] > 10 else "MEDIUM",
                    "detail": (
                        f"{entity} absent from recent period. "
                        f"Was {hist['market_share_pct']}% of market historically."
                    ),
                    "historical_share_pct": hist["market_share_pct"],
                })

        # Volume surges (>2x historical monthly average)
        for entity, curr in current_entities.items():
            if entity in historical_entities:
                hist = historical_entities[entity]
                hist_monthly = hist["volume_mt"] / max(lookback_months, 1)
                if hist_monthly > 0 and curr["volume_mt"] > 2 * hist_monthly:
                    anomalies.append({
                        "type": "VOLUME_SURGE",
                        "entity": entity,
                        "severity": "HIGH",
                        "detail": (
                            f"{entity} volume {curr['volume_mt']:.0f} MT in last 30d "
                            f"vs avg {hist_monthly:.0f} MT/month historically "
                            f"({curr['volume_mt']/hist_monthly:.1f}x normal)"
                        ),
                        "current_volume_mt": curr["volume_mt"],
                        "historical_monthly_mt": round(hist_monthly, 2),
                        "multiplier": round(curr["volume_mt"] / hist_monthly, 1),
                    })

        return sorted(anomalies, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["severity"], 3))

    def compute_origin_switching(
        self,
        records: list[dict],
        entity: str,
        months: int = 6,
    ) -> dict[str, Any]:
        """Detect if an entity is switching origin sources."""
        today = date.today()
        mid = today - timedelta(days=months * 15)  # Midpoint

        recent_origins: dict[str, float] = defaultdict(float)
        earlier_origins: dict[str, float] = defaultdict(float)

        for r in records:
            rd = self._parse_date(r.get("trade_date"))
            if not rd:
                continue
            entity_name = self.resolve_entity(
                r.get("consignee") or r.get("consignor") or ""
            )
            if entity_name != entity:
                continue

            origin = r.get("origin_country", "UNKNOWN")
            qty = r.get("quantity_mt") or 0
            if qty <= 0:
                continue

            if rd >= mid:
                recent_origins[origin] += qty
            elif rd >= today - timedelta(days=months * 30):
                earlier_origins[origin] += qty

        return {
            "entity": entity,
            "recent_origins": dict(recent_origins),
            "earlier_origins": dict(earlier_origins),
            "switching_detected": set(recent_origins.keys()) != set(earlier_origins.keys()),
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
