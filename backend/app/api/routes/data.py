"""Data management routes — ingestion, harvesting, and ground prices."""

from datetime import date, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Query

from app.core.eximpedia import EximpediaClient, EximpediaTokenManager, QueryBuilder
from app.core.normalization import NormalizationPipeline
from app.core.harvester.engine import HarvestEngine
from app.data.commodity_taxonomy import classify_by_hs_code, TAXONOMY
from app.data.harvest_configs import HARVEST_JOBS
from app.schemas.trade import GroundPriceInput, HarvestJobRequest, ShipmentQueryRequest
from .intelligence import store_records

router = APIRouter(prefix="/data", tags=["Data Management"])

normalizer = NormalizationPipeline()

# In-memory ground price store
_ground_prices: list[dict] = []

# Top countries for ad-hoc searches
_SEARCH_COUNTRIES = [
    "INDIA", "VIETNAM", "IVORY COAST", "GHANA", "NIGERIA",
    "TANZANIA", "ETHIOPIA", "INDONESIA", "MALAYSIA", "THAILAND",
    "CHINA", "BRAZIL", "MOZAMBIQUE",
]


@router.post("/query/shipments")
async def query_shipments(req: ShipmentQueryRequest):
    """Direct query to Eximpedia shipment API (for exploration)."""
    payload = QueryBuilder.build_shipment_query(
        start_date=req.start_date,
        end_date=req.end_date,
        trade_type=req.trade_type,
        trade_country=req.trade_country,
        hs_codes=req.hs_codes,
        products=req.products,
        origin_countries=req.origin_countries,
        destination_countries=req.destination_countries,
        page_size=req.page_size,
        page_no=req.page_no,
    )

    client = EximpediaClient(EximpediaTokenManager())
    response = await client.trade_shipment(payload)

    # Normalize records
    raw_records = response.get("data", [])
    normalized = []
    for r in raw_records:
        try:
            n = normalizer.normalize(r, req.trade_type, req.trade_country)
            normalized.append(n)

            # Store by commodity
            if n.get("hct_id"):
                store_records(n["hct_id"], [n])
        except Exception:
            pass

    return {
        "total_records": response.get("total_records", 0),
        "page": req.page_no,
        "raw_count": len(raw_records),
        "normalized_count": len(normalized),
        "records": normalized,
    }


@router.post("/harvest/run")
async def run_harvest(req: HarvestJobRequest):
    """Run harvest jobs to pull data from Eximpedia.

    Optionally filter by job name or priority level.
    Results are normalized and stored for intelligence computations.
    """
    engine = HarvestEngine()

    if req.job_name:
        job = next((j for j in HARVEST_JOBS if j["name"] == req.job_name), None)
        if not job:
            return {"error": f"Job '{req.job_name}' not found"}
        results = [await engine.run_job(job)]
    else:
        results = await engine.run_all_jobs(req.priority)

    # Store normalized records
    for result in results:
        if result["status"] == "SUCCESS":
            for record in result.get("normalized_records", []):
                hct_id = record.get("hct_id")
                if hct_id:
                    store_records(hct_id, [record])
            # Don't send all records back in API response (too large)
            result.pop("normalized_records", None)

    return {"harvest_results": results}


@router.get("/harvest/jobs")
async def list_harvest_jobs():
    """List all configured harvest jobs."""
    return {"jobs": HARVEST_JOBS}


@router.post("/harvest/search")
async def harvest_by_commodity_name(commodity_name: str = Query(..., min_length=2)):
    """Search for a commodity by name, auto-resolve its HS codes,
    and harvest data from top trading countries.

    This lets traders type 'cashew' or 'sesame' and get data immediately
    without knowing HS codes or country configs.
    """
    query_lower = commodity_name.lower().strip()

    # Find matching commodities in taxonomy
    matches = []
    for hct_id, entry in TAXONOMY.items():
        name = entry["hct_name"].lower()
        group = entry["hct_group"].lower()
        if query_lower in name or query_lower in group or query_lower in hct_id.lower():
            matches.append((hct_id, entry))

    if not matches:
        return {
            "status": "NOT_FOUND",
            "message": f"No commodity matching '{commodity_name}' found",
            "available": [e["hct_name"] for e in TAXONOMY.values()],
        }

    engine = HarvestEngine()
    all_results = []

    for hct_id, entry in matches:
        # Extract HS codes for this commodity
        hs_codes_raw = [m["hs_code"] for m in entry.get("hs_mappings", [])]
        # Use 4-digit HS codes for broader matches
        hs_ints = set()
        for hs in hs_codes_raw:
            hs_str = str(hs)
            if len(hs_str) >= 4:
                hs_ints.add(int(hs_str[:4]))
            else:
                hs_ints.add(int(hs_str))

        # Check if there are pre-configured harvest jobs for this commodity
        matching_jobs = [
            j for j in HARVEST_JOBS
            if any(hs in (j.get("hs_codes") or []) for hs in hs_ints)
        ]

        if matching_jobs:
            # Run pre-configured jobs (they have correct countries/filters)
            for job in matching_jobs:
                result = await engine.run_job(job)
                if result["status"] == "SUCCESS":
                    for record in result.get("normalized_records", []):
                        rid = record.get("hct_id")
                        if rid:
                            store_records(rid, [record])
                    result.pop("normalized_records", None)
                all_results.append(result)
        else:
            # No pre-configured job — build ad-hoc harvest from top countries
            hs_list = list(hs_ints)
            for country in _SEARCH_COUNTRIES[:5]:
                for trade_type in ["IMPORT", "EXPORT"]:
                    ad_hoc_job = {
                        "name": f"search_{hct_id}_{country}_{trade_type}".lower(),
                        "trade_type": trade_type,
                        "trade_country": country,
                        "hs_codes": hs_list,
                        "lookback_days": 60,
                    }
                    result = await engine.run_job(ad_hoc_job)
                    if result["status"] == "SUCCESS" and result.get("normalized_count", 0) > 0:
                        for record in result.get("normalized_records", []):
                            rid = record.get("hct_id")
                            if rid:
                                store_records(rid, [record])
                        result.pop("normalized_records", None)
                        all_results.append(result)

    total_loaded = sum(r.get("normalized_count", 0) for r in all_results)

    return {
        "status": "SUCCESS",
        "commodity_query": commodity_name,
        "commodities_matched": [e["hct_name"] for _, e in matches],
        "jobs_executed": len(all_results),
        "total_records_loaded": total_loaded,
        "results": all_results,
    }


@router.get("/harvest/status")
async def harvest_status():
    """Get current data loading status — used by frontend to show progress."""
    from .intelligence import _record_store

    total = sum(len(v) for v in _record_store.values())
    commodities_loaded = sum(1 for v in _record_store.values() if len(v) > 0)
    total_commodities = len(TAXONOMY)

    return {
        "total_records": total,
        "commodities_loaded": commodities_loaded,
        "total_commodities": total_commodities,
        "loading_complete": commodities_loaded > 0,
        "per_commodity": {
            hct_id: {
                "name": TAXONOMY.get(hct_id, {}).get("hct_name", hct_id),
                "count": len(records),
            }
            for hct_id, records in _record_store.items()
            if len(records) > 0
        },
    }


@router.post("/ground-price")
async def submit_ground_price(price: GroundPriceInput):
    """Submit a ground-collected price observation."""
    observation = {
        "observation_id": f"GP-{uuid4().hex[:12]}",
        **price.model_dump(),
        "observation_date": price.observation_date.isoformat(),
        "verified": False,
    }
    _ground_prices.append(observation)
    return {"status": "accepted", "observation": observation}


@router.get("/ground-prices")
async def list_ground_prices(
    hct_id: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    """List ground price observations with optional filters."""
    results = _ground_prices
    if hct_id:
        results = [p for p in results if p.get("hct_id") == hct_id]
    if location:
        results = [p for p in results if location.upper() in (p.get("location") or "").upper()]
    return {"prices": results[-limit:], "total": len(results)}


@router.get("/records/stats")
async def record_stats():
    """Get statistics about stored normalized records."""
    from .intelligence import _record_store

    stats = []
    for hct_id, entry in TAXONOMY.items():
        records = _record_store.get(hct_id, [])
        if records:
            dates = [r.get("trade_date") for r in records if r.get("trade_date")]
            origins = set(r.get("origin_country") for r in records if r.get("origin_country"))
            stats.append({
                "hct_id": hct_id,
                "hct_name": entry["hct_name"],
                "record_count": len(records),
                "date_range": {
                    "earliest": min(dates) if dates else None,
                    "latest": max(dates) if dates else None,
                },
                "origins": list(origins),
            })

    return {"record_stats": stats, "total_records": sum(s["record_count"] for s in stats)}
