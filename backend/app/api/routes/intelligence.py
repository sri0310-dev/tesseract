"""Intelligence API routes — the trader-facing endpoints.

These power the dashboard views: signal feed, commodity deep dive,
corridor explorer, counterparty profiles, and arb scanner.
"""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.core.intelligence import (
    CorridorAnalyzer,
    CounterpartyIntelligence,
    FlowVelocityIndex,
    ImpliedPriceCurve,
    SignalGenerator,
    SupplyDemandTracker,
)
from app.data.commodity_taxonomy import TAXONOMY
from app.data.harvest_configs import PRIORITY_CORRIDORS
from app.data.reference_tables import SEASONAL_PATTERNS
from app.schemas.trade import (
    CommodityAnalysisRequest,
    CorridorCompareRequest,
    CorridorRequest,
    CounterpartyRequest,
    SDDeltaRequest,
)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

# In-memory store for normalized records (replaced by DB in production)
_record_store: dict[str, list[dict]] = {}

ipc_engine = ImpliedPriceCurve()
fvi_engine = FlowVelocityIndex()
sd_engine = SupplyDemandTracker()
counterparty_engine = CounterpartyIntelligence()
corridor_engine = CorridorAnalyzer()
signal_engine = SignalGenerator()


def get_records(hct_id: str) -> list[dict]:
    """Retrieve stored normalized records for a commodity."""
    return _record_store.get(hct_id, [])


def store_records(hct_id: str, records: list[dict]):
    """Store normalized records for a commodity."""
    existing = _record_store.get(hct_id, [])
    seen_ids = {r["record_id"] for r in existing if r.get("record_id")}
    new = [r for r in records if r.get("record_id") not in seen_ids]
    _record_store[hct_id] = existing + new


# ── Signal Feed (Home View) ─────────────────────────────────────

@router.get("/signals")
async def get_signals(
    limit: int = Query(default=20, le=100),
):
    """Get the trading signal feed — the trader's first stop.

    Aggregates signals across all commodities and corridors,
    sorted by severity and recency.
    """
    all_signals = []

    for hct_id, entry in TAXONOMY.items():
        records = get_records(hct_id)
        if not records:
            continue

        # IPC change signals
        today = date.today()
        current_ipc = ipc_engine.compute(records, today)
        week_ago_ipc = ipc_engine.compute(records, today - timedelta(days=7))

        # Group by origin for origin-specific signals
        origins = set()
        for r in records:
            oc = r.get("origin_country")
            if oc:
                origins.add(oc)

        for origin in origins:
            origin_records = [r for r in records if r.get("origin_country") == origin]
            curr = ipc_engine.compute(origin_records, today)
            prev = ipc_engine.compute(origin_records, today - timedelta(days=7))
            sig = signal_engine.generate_from_ipc_change(curr, prev, entry["hct_name"], origin)
            if sig:
                sig["timestamp"] = today.isoformat()
                sig["hct_id"] = hct_id
                all_signals.append(sig)

        # FVI signals per corridor
        for corridor in PRIORITY_CORRIDORS:
            if corridor["commodity"] != hct_id:
                continue
            corridor_records = [
                r for r in records
                if r.get("origin_country") in corridor.get("origins", [])
            ]
            fvi_result = fvi_engine.compute_seasonally_adjusted(corridor_records, hct_id, today)
            sig = signal_engine.generate_from_fvi(fvi_result, corridor["name"])
            if sig:
                sig["timestamp"] = today.isoformat()
                sig["hct_id"] = hct_id
                all_signals.append(sig)

    # Sort by severity then timestamp
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_signals.sort(key=lambda s: severity_order.get(s.get("severity"), 3))

    return {"signals": all_signals[:limit], "total": len(all_signals)}


# ── Commodity Deep Dive ──────────────────────────────────────────

@router.get("/commodities")
async def list_commodities():
    """List all tracked commodities with quick stats."""
    result = []
    for hct_id, entry in TAXONOMY.items():
        records = get_records(hct_id)
        today = date.today()
        ipc = ipc_engine.compute(records, today) if records else None

        result.append({
            "hct_id": hct_id,
            "hct_name": entry["hct_name"],
            "hct_group": entry["hct_group"],
            "hct_supergroup": entry["hct_supergroup"],
            "record_count": len(records),
            "current_price_usd": ipc["price_usd_per_mt"] if ipc else None,
            "price_confidence": ipc["confidence"] if ipc else "NONE",
            "quality_grades": entry.get("quality_grades", []),
        })

    return {"commodities": result}


@router.post("/commodity/deep-dive")
async def commodity_deep_dive(req: CommodityAnalysisRequest):
    """Full analysis for a single commodity.

    Returns IPC time series, volume breakdown, top counterparties,
    FVI, and S&D signals — everything a trader needs for one commodity.
    """
    records = get_records(req.hct_id)

    # Filter by origin/destination if specified
    filtered = records
    if req.origin_countries:
        filtered = [r for r in filtered if r.get("origin_country") in req.origin_countries]
    if req.destination_countries:
        filtered = [r for r in filtered if r.get("destination_country") in req.destination_countries]

    # IPC time series
    ipc_series = ipc_engine.compute_time_series(filtered, req.start_date, req.end_date)

    # Current IPC
    current_ipc = ipc_engine.compute(filtered, req.end_date)

    # FVI
    fvi = fvi_engine.compute_seasonally_adjusted(filtered, req.hct_id, req.end_date)

    # Volume breakdown by origin
    sd = sd_engine.compute_cumulative_flows(filtered, req.start_date, req.end_date)

    # Top buyers and sellers
    buyers = counterparty_engine.compute_market_shares(
        filtered, "consignee", req.start_date, req.end_date, top_n=10
    )
    sellers = counterparty_engine.compute_market_shares(
        filtered, "consignor", req.start_date, req.end_date, top_n=10
    )

    # Seasonal context
    seasonal = SEASONAL_PATTERNS.get(req.hct_id)

    entry = TAXONOMY.get(req.hct_id, {})

    return {
        "commodity": {
            "hct_id": req.hct_id,
            "hct_name": entry.get("hct_name", "Unknown"),
            "hct_group": entry.get("hct_group", "Unknown"),
        },
        "current_ipc": current_ipc,
        "ipc_series": ipc_series,
        "fvi": fvi,
        "volume_summary": sd,
        "top_buyers": buyers,
        "top_sellers": sellers,
        "seasonal_patterns": seasonal,
        "period": {"start": req.start_date.isoformat(), "end": req.end_date.isoformat()},
    }


# ── Corridor Explorer ────────────────────────────────────────────

@router.get("/corridors")
async def list_corridors():
    """List all priority corridors."""
    result = []
    for corridor in PRIORITY_CORRIDORS:
        hct_id = corridor["commodity"]
        records = get_records(hct_id)
        corridor_records = [
            r for r in records
            if r.get("origin_country") in corridor.get("origins", [])
        ]
        ipc = ipc_engine.compute(corridor_records) if corridor_records else None

        result.append({
            **corridor,
            "record_count": len(corridor_records),
            "current_fob": ipc["price_usd_per_mt"] if ipc else None,
            "price_confidence": ipc["confidence"] if ipc else "NONE",
        })

    return {"corridors": result}


@router.post("/corridor/analyze")
async def analyze_corridor(req: CorridorRequest):
    """Compute FOB, freight, insurance, port charges, and implied CIF for a corridor."""
    records = get_records(req.hct_id)
    return corridor_engine.compute_fab(
        records, req.origin_country, req.origin_port, req.dest_port, req.target_date
    )


@router.post("/corridor/compare")
async def compare_corridors(req: CorridorCompareRequest):
    """Compare multiple origins delivering to the same destination."""
    records = get_records(req.hct_id)
    return corridor_engine.compare_origins(records, req.origins, req.dest_port, req.target_date)


# ── Counterparty Intelligence ────────────────────────────────────

@router.post("/counterparty/market-shares")
async def counterparty_market_shares(req: CounterpartyRequest):
    """Get market share breakdown for buyers or sellers."""
    records = get_records(req.hct_id)
    return counterparty_engine.compute_market_shares(
        records, req.party_type, req.start_date, req.end_date, req.top_n
    )


@router.post("/counterparty/anomalies")
async def counterparty_anomalies(req: CounterpartyRequest):
    """Detect new entrants, withdrawals, and volume surges."""
    records = get_records(req.hct_id)
    return {"anomalies": counterparty_engine.detect_anomalies(records, records, req.party_type)}


# ── S&D Tracker ──────────────────────────────────────────────────

@router.post("/sd/delta")
async def sd_delta(req: SDDeltaRequest):
    """Compute S&D delta vs. consensus estimate."""
    records = get_records(req.hct_id)
    return sd_engine.compute_sd_delta(
        records, req.consensus_annual_mt, req.crop_year_start, req.target_date
    )


@router.post("/sd/flows")
async def sd_flows(req: CommodityAnalysisRequest):
    """Get cumulative trade flows for a commodity over a period."""
    records = get_records(req.hct_id)
    filtered = records
    if req.origin_countries:
        filtered = [r for r in filtered if r.get("origin_country") in req.origin_countries]
    return sd_engine.compute_cumulative_flows(filtered, req.start_date, req.end_date)


# ── Arbitrage Scanner ────────────────────────────────────────────

@router.get("/arbitrage/{hct_id}")
async def arbitrage_scan(hct_id: str):
    """Scan for arbitrage opportunities across origins for a commodity."""
    records = get_records(hct_id)
    corridors_for_commodity = [
        c for c in PRIORITY_CORRIDORS if c["commodity"] == hct_id
    ]

    # Build corridor dicts with origin_country for arb scan
    corridor_dicts = []
    for c in corridors_for_commodity:
        for origin in c.get("origins", []):
            corridor_dicts.append({"origin_country": origin})

    arbs = corridor_engine.find_arbitrage(records, corridor_dicts)
    return {"commodity": hct_id, "opportunities": arbs}
