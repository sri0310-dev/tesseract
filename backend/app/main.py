"""Hectar Commodity Flow Intelligence Suite — FastAPI Application.

The backend that transforms raw global trade data into
actionable commodity intelligence for traders.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import intelligence, data
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Predictive intelligence platform transforming raw global customs/trade data "
        "into actionable commodity pricing signals, supply-demand intelligence, "
        "and counterparty insights."
    ),
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
