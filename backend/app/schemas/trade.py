"""Pydantic schemas for API request/response validation."""

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────

class DateRangeRequest(BaseModel):
    start_date: date
    end_date: date


class ShipmentQueryRequest(BaseModel):
    start_date: date
    end_date: date
    trade_type: str = Field(..., pattern="^(IMPORT|EXPORT)$")
    trade_country: str
    hs_codes: Optional[list[int]] = None
    products: Optional[list[str]] = None
    origin_countries: Optional[list[str]] = None
    destination_countries: Optional[list[str]] = None
    page_size: int = Field(default=1000, le=1000)
    page_no: int = Field(default=1, ge=1)


class CommodityAnalysisRequest(BaseModel):
    hct_id: str
    start_date: date
    end_date: date
    origin_countries: Optional[list[str]] = None
    destination_countries: Optional[list[str]] = None


class CorridorRequest(BaseModel):
    hct_id: str
    origin_country: str
    origin_port: str
    dest_port: str
    target_date: Optional[date] = None


class CorridorCompareRequest(BaseModel):
    hct_id: str
    origins: list[dict]  # [{country, port}, ...]
    dest_port: str
    target_date: Optional[date] = None


class SDDeltaRequest(BaseModel):
    hct_id: str
    consensus_annual_mt: float
    crop_year_start: date
    target_date: Optional[date] = None


class CounterpartyRequest(BaseModel):
    hct_id: str
    party_type: str = Field(default="consignee", pattern="^(consignee|consignor)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    top_n: int = Field(default=20, le=50)


class GroundPriceInput(BaseModel):
    hct_id: str
    price: float
    currency: str = "USD"
    unit: str = "MT"
    incoterm: str = "FOB"
    location: str
    quality_grade: Optional[str] = None
    source_type: str
    source_name: Optional[str] = None
    observation_date: date
    notes: Optional[str] = None


class HarvestJobRequest(BaseModel):
    job_name: Optional[str] = None
    priority: Optional[int] = None


# ── Response schemas ─────────────────────────────────────────────

class IPCResponse(BaseModel):
    price_usd_per_mt: Optional[float]
    confidence: str
    n_records: int
    volume_mt: float
    price_iqr: Optional[float]
    price_min: Optional[float]
    price_max: Optional[float]
    price_mean: Optional[float]
    window_start: Optional[str]
    window_end: Optional[str]


class FVIResponse(BaseModel):
    fvi_raw: Optional[float]
    fvi_adjusted: Optional[float] = None
    signal: str
    signal_adjusted: Optional[str] = None
    volume_recent_mt: float
    volume_baseline_mt: float
    seasonal_factor: Optional[float] = None


class SignalResponse(BaseModel):
    signal_type: str
    severity: str
    headline: str
    detail: dict[str, Any]


class CommodityOverview(BaseModel):
    hct_id: str
    hct_name: str
    hct_group: str
    current_ipc: Optional[IPCResponse] = None
    fvi: Optional[FVIResponse] = None
    total_volume_mt: float = 0
    record_count: int = 0
    top_origins: list[dict] = []
    top_buyers: list[dict] = []
    signals: list[SignalResponse] = []
