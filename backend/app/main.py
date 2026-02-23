"""Hectar Commodity Flow Intelligence Suite — FastAPI Application.

The backend that transforms raw global trade data into
actionable commodity intelligence for traders.
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
    """Harvest priority-1 commodity data on startup so traders see data immediately."""
    from app.core.harvester.engine import HarvestEngine
    from app.data.harvest_configs import HARVEST_JOBS
    from app.api.routes.intelligence import store_records

    logger.info("Starting initial data harvest (priority 1 jobs)...")
    engine = HarvestEngine()

    p1_jobs = [j for j in HARVEST_JOBS if j.get("priority", 99) <= 1]
    for job in p1_jobs:
        try:
            result = await engine.run_job(job)
            if result["status"] == "SUCCESS":
                for record in result.get("normalized_records", []):
                    hct_id = record.get("hct_id")
                    if hct_id:
                        store_records(hct_id, [record])
                logger.info(
                    f"  {result['job_name']}: {result['normalized_count']} records loaded"
                )
            else:
                logger.warning(f"  {result['job_name']}: {result.get('error', 'unknown error')}")
        except Exception as e:
            logger.warning(f"  {job['name']}: failed ({e})")

    logger.info("Initial harvest complete.")


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
