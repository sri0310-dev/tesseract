"""Hectar Commodity Flow Intelligence Suite — FastAPI Application.

The backend that transforms raw global trade data into
actionable commodity intelligence for traders.

Startup strategy (budget-aware):
- 100 API calls/day limit → harvest only 4 highest-priority India jobs on boot
- Background task harvests remaining P1 jobs over the next few minutes
- P2 jobs are deferred to on-demand or scheduled refresh
- Each job ~1-3 API pages = 1-3 calls. 4 jobs ≈ 8-12 calls on startup.
"""

import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import intelligence, data
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def _initial_harvest():
    """Smart startup harvest — budget-aware, fast first data.

    Strategy:
    1. Immediate batch (4 India-based jobs): shows data in ~30s
    2. Background batch (remaining P1 jobs): fills in over next 2-3 min
    3. Respects daily budget (60 calls for harvests)
    """
    from app.core.harvester.engine import HarvestEngine
    from app.core.budget import APIBudgetTracker
    from app.data.harvest_configs import HARVEST_JOBS
    from app.api.routes.intelligence import store_records

    engine = HarvestEngine()
    budget = APIBudgetTracker()

    # Phase 1: India jobs (fastest, most reliable data source)
    india_p1 = [
        j for j in HARVEST_JOBS
        if j.get("priority", 99) <= 1 and j["trade_country"] == "INDIA"
    ]
    other_p1 = [
        j for j in HARVEST_JOBS
        if j.get("priority", 99) <= 1 and j["trade_country"] != "INDIA"
    ]

    logger.info(
        f"Startup harvest: {len(india_p1)} India jobs (immediate), "
        f"{len(other_p1)} other P1 jobs (background)"
    )

    async def _run_job(job: dict):
        if not budget.can_harvest():
            logger.warning(f"  Skipping {job['name']}: daily harvest budget exhausted")
            return
        try:
            result = await engine.run_job(job)
            budget.record_call("harvest")
            if result["status"] == "SUCCESS":
                for record in result.get("normalized_records", []):
                    hct_id = record.get("hct_id")
                    if hct_id:
                        store_records(hct_id, [record])
                logger.info(
                    f"  {result['job_name']}: {result['normalized_count']} records"
                )
            else:
                logger.warning(
                    f"  {result['job_name']}: {result.get('error', 'unknown')}"
                )
        except Exception as e:
            logger.warning(f"  {job['name']}: failed ({e})")

    # Phase 1: Immediate (India data)
    for job in india_p1:
        await _run_job(job)

    logger.info(
        f"Phase 1 complete. Budget: {budget.status['daily_calls_remaining']} calls remaining"
    )

    # Phase 2: Background (other P1 jobs — with small delay between to avoid 429)
    for job in other_p1:
        await asyncio.sleep(2)
        await _run_job(job)

    logger.info(f"Startup harvest complete. Budget: {budget.status}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire-and-forget: harvest data in background so the server starts immediately
    asyncio.create_task(_initial_harvest())
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Predictive intelligence platform transforming raw global customs/trade data "
        "into actionable commodity pricing signals, supply-demand intelligence, "
        "and counterparty insights."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
