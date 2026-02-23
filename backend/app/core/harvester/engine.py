"""Data Harvester — orchestrates pulling data from Eximpedia.

Runs harvest jobs defined in harvest_configs.py, handles pagination,
deduplication, and normalization of incoming records.
"""

import logging
from datetime import date, timedelta
from typing import Any

from app.core.eximpedia import EximpediaClient, EximpediaTokenManager, QueryBuilder
from app.core.normalization import NormalizationPipeline
from app.data.harvest_configs import HARVEST_JOBS

logger = logging.getLogger(__name__)


class HarvestEngine:
    """Orchestrate data harvesting from Eximpedia API."""

    def __init__(self):
        self.client = EximpediaClient(EximpediaTokenManager())
        self.normalizer = NormalizationPipeline()
        self.seen_record_ids: set[str] = set()

    async def run_job(self, job_config: dict) -> dict[str, Any]:
        """Execute a single harvest job.

        Args:
            job_config: Harvest job configuration dict

        Returns:
            Summary with record counts and any errors
        """
        name = job_config["name"]
        lookback = job_config.get("lookback_days", 30)
        end = date.today()
        start = end - timedelta(days=lookback)

        logger.info(f"Starting harvest job: {name} ({start} to {end})")

        payload = QueryBuilder.build_shipment_query(
            start_date=start,
            end_date=end,
            trade_type=job_config["trade_type"],
            trade_country=job_config["trade_country"],
            hs_codes=job_config.get("hs_codes"),
            products=job_config.get("products"),
            origin_countries=job_config.get("origin_countries"),
            destination_countries=job_config.get("destination_countries"),
        )

        try:
            raw_records = await self.client.trade_shipment_all(payload)
        except Exception as e:
            logger.error(f"Harvest job {name} failed: {e}")
            return {
                "job_name": name,
                "status": "FAILED",
                "error": str(e),
                "raw_count": 0,
                "normalized_count": 0,
            }

        # Deduplicate
        unique_records = []
        for r in raw_records:
            rid = r.get("RECORD_ID")
            if rid and rid not in self.seen_record_ids:
                self.seen_record_ids.add(rid)
                unique_records.append(r)

        # Normalize
        normalized = []
        errors = 0
        for r in unique_records:
            try:
                n = self.normalizer.normalize(
                    r, job_config["trade_type"], job_config["trade_country"]
                )
                normalized.append(n)
            except Exception as e:
                errors += 1
                logger.warning(f"Normalization error in {name}: {e}")

        logger.info(
            f"Job {name}: {len(raw_records)} raw → {len(unique_records)} unique → "
            f"{len(normalized)} normalized ({errors} errors)"
        )

        return {
            "job_name": name,
            "status": "SUCCESS",
            "raw_count": len(raw_records),
            "unique_count": len(unique_records),
            "normalized_count": len(normalized),
            "error_count": errors,
            "date_range": f"{start} to {end}",
            "normalized_records": normalized,
        }

    async def run_all_jobs(self, priority: int | None = None) -> list[dict]:
        """Run all configured harvest jobs (optionally filtered by priority)."""
        jobs = HARVEST_JOBS
        if priority is not None:
            jobs = [j for j in jobs if j.get("priority", 99) <= priority]

        results = []
        for job in jobs:
            result = await self.run_job(job)
            results.append(result)

        return results
