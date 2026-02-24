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

    Returns price-by-grade-and-origin, volume momentum, top counterparties
    with quality/price detail, and S&D context — what a trader actually needs.
    """
    records = get_records(req.hct_id)

    # Filter by origin/destination if specified
    filtered = records
    if req.origin_countries:
        filtered = [r for r in filtered if r.get("origin_country") in req.origin_countries]
    if req.destination_countries:
        filtered = [r for r in filtered if r.get("destination_country") in req.destination_countries]

    entry = TAXONOMY.get(req.hct_id, {})
    period_start = req.start_date.isoformat()
    period_end = req.end_date.isoformat()

    # ── Price by Grade × Origin ──────────────────────────────────
    # Group records by (quality_grade, origin_country) and compute
    # volume-weighted avg price for each segment.
    price_segments: dict[tuple[str, str], dict] = {}
    for r in filtered:
        td = r.get("trade_date", "")
        if td < period_start or td > period_end:
            continue
        grade = "Unknown"
        q = r.get("quality_estimate")
        if isinstance(q, dict) and q.get("grade"):
            grade = q["grade"]
        origin = r.get("origin_country") or "Unknown"
        key = (grade, origin)
        if key not in price_segments:
            price_segments[key] = {
                "grade": grade,
                "origin": origin,
                "total_value": 0.0,
                "total_mt": 0.0,
                "shipments": 0,
                "prices": [],
            }
        seg = price_segments[key]
        qty = r.get("quantity_mt") or 0
        price = r.get("fob_usd_per_mt")
        fob_total = r.get("fob_usd_total") or 0
        seg["total_mt"] += qty
        seg["total_value"] += fob_total
        seg["shipments"] += 1
        if price and r.get("price_status") == "NORMAL":
            seg["prices"].append(price)

    price_by_grade = []
    for seg in sorted(price_segments.values(), key=lambda s: s["total_mt"], reverse=True):
        avg_price = None
        if seg["total_mt"] > 0 and seg["total_value"] > 0:
            avg_price = round(seg["total_value"] / seg["total_mt"], 2)
        elif seg["prices"]:
            avg_price = round(sum(seg["prices"]) / len(seg["prices"]), 2)

        price_range = None
        if len(seg["prices"]) >= 2:
            price_range = {"min": round(min(seg["prices"]), 2), "max": round(max(seg["prices"]), 2)}

        price_by_grade.append({
            "grade": seg["grade"],
            "origin": seg["origin"],
            "fob_usd_per_mt": avg_price,
            "volume_mt": round(seg["total_mt"], 2),
            "shipments": seg["shipments"],
            "price_range": price_range,
        })

    # ── Volume Momentum (plain language) ─────────────────────────
    # Compare last 7 days vs prior 7 days. Simple, clear.
    recent_cutoff = req.end_date - timedelta(days=7)
    prior_start = req.end_date - timedelta(days=14)
    vol_recent = 0.0
    vol_prior = 0.0
    ship_recent = 0
    ship_prior = 0
    for r in filtered:
        td = r.get("trade_date", "")
        qty = r.get("quantity_mt") or 0
        if td > recent_cutoff.isoformat():
            vol_recent += qty
            ship_recent += 1
        elif td > prior_start.isoformat():
            vol_prior += qty
            ship_prior += 1

    if vol_prior > 0:
        momentum_pct = round((vol_recent - vol_prior) / vol_prior * 100, 1)
    else:
        momentum_pct = None

    if momentum_pct is not None:
        if momentum_pct > 20:
            momentum_signal = "ACCELERATING"
            momentum_text = f"Shipments surging — up {momentum_pct}% vs prior week"
        elif momentum_pct > 5:
            momentum_signal = "PICKING_UP"
            momentum_text = f"Shipments picking up — {momentum_pct}% above prior week"
        elif momentum_pct > -5:
            momentum_signal = "STEADY"
            momentum_text = "Shipment pace steady week-over-week"
        elif momentum_pct > -20:
            momentum_signal = "SLOWING"
            momentum_text = f"Shipments slowing — down {abs(momentum_pct)}% vs prior week"
        else:
            momentum_signal = "DROPPING"
            momentum_text = f"Shipments dropping — down {abs(momentum_pct)}% vs prior week"
    else:
        momentum_signal = "INSUFFICIENT_DATA"
        momentum_text = "Not enough data to compare week-over-week"

    volume_momentum = {
        "recent_7d_mt": round(vol_recent, 1),
        "prior_7d_mt": round(vol_prior, 1),
        "recent_7d_shipments": ship_recent,
        "prior_7d_shipments": ship_prior,
        "change_pct": momentum_pct,
        "signal": momentum_signal,
        "description": momentum_text,
        "recent_period": f"{recent_cutoff.isoformat()} to {period_end}",
        "prior_period": f"{prior_start.isoformat()} to {recent_cutoff.isoformat()}",
    }

    # ── Top Buyers with quality + price context ──────────────────
    def _enrich_counterparties(party_field: str) -> list[dict]:
        """Build counterparty list with the quality grades and avg price they trade."""
        party_data: dict[str, dict] = {}
        for r in filtered:
            td = r.get("trade_date", "")
            if td < period_start or td > period_end:
                continue
            name = r.get(party_field) or "Unknown"
            if name not in party_data:
                party_data[name] = {
                    "entity": name,
                    "volume_mt": 0.0,
                    "value_usd": 0.0,
                    "shipments": 0,
                    "grades": {},
                    "origins": {},
                    "prices": [],
                }
            pd = party_data[name]
            pd["volume_mt"] += r.get("quantity_mt") or 0
            pd["value_usd"] += r.get("fob_usd_total") or 0
            pd["shipments"] += 1
            price = r.get("fob_usd_per_mt")
            if price and r.get("price_status") == "NORMAL":
                pd["prices"].append(price)
            q = r.get("quality_estimate")
            if isinstance(q, dict) and q.get("grade"):
                g = q["grade"]
                pd["grades"][g] = pd["grades"].get(g, 0) + 1
            origin = r.get("origin_country")
            if origin:
                pd["origins"][origin] = pd["origins"].get(origin, 0) + (r.get("quantity_mt") or 0)

        total_vol = sum(p["volume_mt"] for p in party_data.values())
        result = []
        for pd in sorted(party_data.values(), key=lambda x: x["volume_mt"], reverse=True)[:10]:
            avg_price = None
            if pd["volume_mt"] > 0 and pd["value_usd"] > 0:
                avg_price = round(pd["value_usd"] / pd["volume_mt"], 2)
            elif pd["prices"]:
                avg_price = round(sum(pd["prices"]) / len(pd["prices"]), 2)

            top_grades = sorted(pd["grades"].items(), key=lambda x: x[1], reverse=True)[:3]
            top_origins = sorted(pd["origins"].items(), key=lambda x: x[1], reverse=True)[:3]

            result.append({
                "entity": pd["entity"],
                "volume_mt": round(pd["volume_mt"], 2),
                "value_usd": round(pd["value_usd"], 2),
                "shipments": pd["shipments"],
                "market_share_pct": round(pd["volume_mt"] / total_vol * 100, 1) if total_vol > 0 else 0,
                "avg_price_per_mt": avg_price,
                "top_grades": [{"grade": g, "count": c} for g, c in top_grades],
                "top_origins": [{"country": o, "volume_mt": round(v, 1)} for o, v in top_origins],
            })
        return result

    enriched_buyers = _enrich_counterparties("consignee")
    enriched_sellers = _enrich_counterparties("consignor")

    # ── IPC time series (price trend) ────────────────────────────
    ipc_series = ipc_engine.compute_time_series(filtered, req.start_date, req.end_date)
    current_ipc = ipc_engine.compute(filtered, req.end_date)

    # ── Volume breakdown by origin ───────────────────────────────
    sd = sd_engine.compute_cumulative_flows(filtered, req.start_date, req.end_date)

    return {
        "commodity": {
            "hct_id": req.hct_id,
            "hct_name": entry.get("hct_name", "Unknown"),
            "hct_group": entry.get("hct_group", "Unknown"),
        },
        "period": {"start": period_start, "end": period_end},
        "price_by_grade": price_by_grade,
        "volume_momentum": volume_momentum,
        "top_buyers": enriched_buyers,
        "top_sellers": enriched_sellers,
        "current_ipc": current_ipc,
        "ipc_series": ipc_series,
        "volume_summary": sd,
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


# ── Counterparty Search & Deep Intelligence ───────────────────

@router.get("/counterparty/search")
async def counterparty_search(
    name: str = Query(..., min_length=2, description="Company name to search"),
    trade_country: str = Query(default="INDIA", description="Country to search in"),
    trade_type: str = Query(default="IMPORT", description="IMPORT or EXPORT"),
    months: int = Query(default=6, le=12, description="Months of history"),
):
    """Search for a counterparty by name and get full intelligence profile.

    Searches cached data first, then optionally fetches from Eximpedia
    if the counterparty is not found locally.
    """
    from app.core.budget import APIBudgetTracker

    name_upper = name.upper().strip()
    today = date.today()
    start = today - timedelta(days=months * 30)
    budget = APIBudgetTracker()

    # Step 1: Search all cached records for this counterparty
    party_field = "consignee" if trade_type.upper() == "IMPORT" else "consignor"
    local_records = []
    for hct_id, records in _record_store.items():
        for r in records:
            party = (r.get(party_field) or "").upper()
            if name_upper in party:
                local_records.append(r)

    # Step 2: If insufficient local data and budget allows, fetch from API
    api_fetched = False
    if len(local_records) < 10 and budget.can_search():
        try:
            from app.core.eximpedia import EximpediaClient, EximpediaTokenManager
            from app.core.normalization import NormalizationPipeline

            client = EximpediaClient(EximpediaTokenManager())
            normalizer = NormalizationPipeline()

            filter_type = "CONSIGNEE" if trade_type.upper() == "IMPORT" else "CONSIGNOR"
            payload = {
                "DateRange": {
                    "start_date": start.isoformat(),
                    "end_date": today.isoformat(),
                },
                "TradeType": trade_type.upper(),
                "TradeCountry": trade_country.upper(),
                "page_size": 1000,
                "page_no": 1,
                "sort": "DATE",
                "sort_type": "desc",
                "PrimarySearch": {
                    "FILTER": filter_type,
                    "VALUES": [name_upper],
                    "SearchType": "CONTAIN",
                },
            }

            try:
                response = await client.trade_shipment(payload)
                budget.record_call("search")
                raw_records = response.get("data", [])
                for r in raw_records:
                    try:
                        n = normalizer.normalize(r, trade_type, trade_country)
                        local_records.append(n)
                        if n.get("hct_id"):
                            store_records(n["hct_id"], [n])
                    except Exception:
                        pass
                api_fetched = True
            except Exception:
                pass
        except Exception:
            pass

    if not local_records:
        return {
            "status": "NOT_FOUND",
            "query": name,
            "message": f"No shipments found for '{name}' in {trade_country} {trade_type}",
            "budget": budget.status,
        }

    # Step 3: Build intelligence profile
    # Recent shipments (last 20)
    sorted_records = sorted(
        local_records, key=lambda r: r.get("trade_date") or "", reverse=True
    )
    recent_shipments = sorted_records[:20]

    # Price analysis
    prices_with_date = [
        (r["trade_date"], r["fob_usd_per_mt"])
        for r in sorted_records
        if r.get("fob_usd_per_mt") and r.get("trade_date")
    ]
    avg_price = (
        sum(p for _, p in prices_with_date) / len(prices_with_date)
        if prices_with_date
        else None
    )

    # Price time series
    price_series = [
        {"date": d, "price_usd_per_mt": round(p, 2)}
        for d, p in prices_with_date
    ]

    # Volume time series
    volume_by_month: dict[str, float] = {}
    for r in sorted_records:
        d = r.get("trade_date", "")[:7]  # YYYY-MM
        if d:
            volume_by_month[d] = volume_by_month.get(d, 0) + (r.get("quantity_mt") or 0)
    volume_series = [
        {"month": m, "volume_mt": round(v, 2)}
        for m, v in sorted(volume_by_month.items())
    ]

    # Commodity breakdown
    commodity_volumes: dict[str, dict] = {}
    for r in sorted_records:
        cid = r.get("hct_id") or "UNKNOWN"
        cname = r.get("hct_name") or "Unknown"
        if cid not in commodity_volumes:
            commodity_volumes[cid] = {"name": cname, "volume_mt": 0, "value_usd": 0, "shipments": 0}
        commodity_volumes[cid]["volume_mt"] += r.get("quantity_mt") or 0
        commodity_volumes[cid]["value_usd"] += r.get("fob_usd_total") or 0
        commodity_volumes[cid]["shipments"] += 1

    # Origin/destination breakdown
    geo_volumes: dict[str, float] = {}
    geo_field = "origin_country" if trade_type.upper() == "IMPORT" else "destination_country"
    for r in sorted_records:
        g = r.get(geo_field) or "UNKNOWN"
        geo_volumes[g] = geo_volumes.get(g, 0) + (r.get("quantity_mt") or 0)

    total_volume = sum(r.get("quantity_mt") or 0 for r in sorted_records)
    total_value = sum(r.get("fob_usd_total") or 0 for r in sorted_records)

    # Market comparison: how does this party's avg price compare to market?
    market_prices = []
    for r in sorted_records:
        hct_id = r.get("hct_id")
        if hct_id:
            mkt_records = get_records(hct_id)
            if mkt_records:
                mkt_ipc = ipc_engine.compute(mkt_records)
                if mkt_ipc.get("price_usd_per_mt"):
                    market_prices.append({
                        "commodity": r.get("hct_name"),
                        "hct_id": hct_id,
                        "market_price": mkt_ipc["price_usd_per_mt"],
                        "party_avg_price": avg_price,
                    })
                    break  # One comparison is enough for overview

    # Hunger signal: is volume trend increasing or decreasing?
    hunger_signal = "STABLE"
    if len(volume_series) >= 3:
        recent_avg = sum(v["volume_mt"] for v in volume_series[-2:]) / 2
        older_avg = sum(v["volume_mt"] for v in volume_series[:-2]) / max(1, len(volume_series) - 2)
        if older_avg > 0:
            ratio = recent_avg / older_avg
            if ratio > 1.3:
                hunger_signal = "INCREASING"
            elif ratio < 0.7:
                hunger_signal = "DECREASING"

    # Quality breakdown
    quality_counts: dict[str, int] = {}
    for r in sorted_records:
        q = r.get("quality_estimate", {})
        if isinstance(q, dict):
            grade = q.get("grade", "Unknown")
        else:
            grade = "Unknown"
        quality_counts[grade] = quality_counts.get(grade, 0) + 1

    return {
        "status": "SUCCESS",
        "query": name,
        "counterparty_name": sorted_records[0].get(party_field) if sorted_records else name,
        "trade_type": trade_type.upper(),
        "trade_country": trade_country,
        "data_source": "api" if api_fetched else "cache",
        "summary": {
            "total_shipments": len(sorted_records),
            "total_volume_mt": round(total_volume, 2),
            "total_value_usd": round(total_value, 2),
            "avg_price_per_mt": round(avg_price, 2) if avg_price else None,
            "date_range": {
                "earliest": sorted_records[-1].get("trade_date") if sorted_records else None,
                "latest": sorted_records[0].get("trade_date") if sorted_records else None,
            },
            "hunger_signal": hunger_signal,
        },
        "price_series": price_series,
        "volume_series": volume_series,
        "commodity_breakdown": [
            {"hct_id": k, **v} for k, v in sorted(
                commodity_volumes.items(), key=lambda x: x[1]["volume_mt"], reverse=True
            )
        ],
        "geography_breakdown": [
            {"country": k, "volume_mt": round(v, 2), "share_pct": round(v / total_volume * 100, 1) if total_volume > 0 else 0}
            for k, v in sorted(geo_volumes.items(), key=lambda x: x[1], reverse=True)
        ],
        "quality_breakdown": [
            {"grade": k, "count": v} for k, v in sorted(quality_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        "market_comparison": market_prices,
        "recent_shipments": [
            {
                "date": r.get("trade_date"),
                "commodity": r.get("hct_name"),
                "origin": r.get("origin_country"),
                "destination": r.get("destination_country"),
                "quantity_mt": r.get("quantity_mt"),
                "fob_usd_per_mt": r.get("fob_usd_per_mt"),
                "quality": r.get("quality_estimate"),
                "port": r.get("origin_port") or r.get("destination_port"),
            }
            for r in recent_shipments
        ],
        "budget": budget.status,
    }


# ── Budget Status ─────────────────────────────────────────────

@router.get("/budget")
async def api_budget():
    """Get current API budget status."""
    from app.core.budget import APIBudgetTracker
    return APIBudgetTracker().status
