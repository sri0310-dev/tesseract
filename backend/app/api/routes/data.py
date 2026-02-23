"""Data management routes — ingestion, harvesting, and ground prices."""

from datetime import date
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Query

from app.core.eximpedia import EximpediaClient, EximpediaTokenManager, QueryBuilder
from app.core.normalization import NormalizationPipeline
from app.core.harvester.engine import HarvestEngine
from app.data.commodity_taxonomy import classify_by_hs_code
from app.data.harvest_configs import HARVEST_JOBS
from app.schemas.trade import GroundPriceInput, HarvestJobRequest, ShipmentQueryRequest
from .intelligence import store_records

router = APIRouter(prefix="/data", tags=["Data Management"])

normalizer = NormalizationPipeline()

# In-memory ground price store
_ground_prices: list[dict] = []


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


@router.post("/ground-price")
async def submit_ground_price(price: GroundPriceInput):
    """Submit a ground-collected price observation.

    Used by field agents and analysts to enter broker quotes,
    auction results, and market observations.
    """
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
    from app.data.commodity_taxonomy import TAXONOMY

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
