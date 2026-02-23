"""Normalization pipeline — the core competitive moat.

Transforms raw Eximpedia trade records into comparable, standardized
records with FOB USD pricing, metric tonne quantities, and quality
grades. Every single record flows through this before it reaches
the intelligence layer.
"""

from datetime import datetime
from typing import Any

from app.data.commodity_taxonomy import classify_by_hs_code
from app.data.reference_tables import (
    calc_insurance,
    convert_to_mt,
    infer_incoterm,
    lookup_freight,
    lookup_port_charges,
)
from .quality_parser import parse_quality


class NormalizationPipeline:
    """Process raw trade records into normalized, comparable records."""

    def normalize(self, raw: dict[str, Any], trade_type: str, trade_country: str) -> dict:
        """Normalize a single raw record from Eximpedia.

        Steps:
        1. Determine declared incoterm basis
        2. Extract best available price in USD
        3. Standardize quantity to metric tonnes
        4. Normalize price to FOB USD
        5. Calculate unit price (USD/MT)
        6. Classify commodity via HCT
        7. Infer quality/grade
        8. Flag outliers
        """
        trade_type = trade_type.upper()
        trade_country = trade_country.upper()

        # Step 1: Incoterm basis
        incoterm = infer_incoterm(trade_type, trade_country)

        # Step 2: Price extraction
        price_usd, price_source = self._extract_price(raw, trade_country)

        # Step 3: Commodity classification
        hs_code = str(raw.get("HS_CODE", "") or "")
        hct = classify_by_hs_code(hs_code, trade_country)
        hct_id = hct["hct_id"] if hct else None
        hct_name = hct["hct_name"] if hct else "Unclassified"
        hct_group = hct.get("hct_group", "Unknown") if hct else "Unknown"

        # Step 4: Quantity standardization
        quantity_mt, unit_status = convert_to_mt(
            raw.get("QUANTITY") or raw.get("STD_QUANTITY"),
            raw.get("UNIT") or raw.get("STD_UNIT"),
            hct_name,
        )

        # If STD_QUANTITY and STD_UNIT available and primary failed
        if unit_status == "UNRESOLVABLE" and raw.get("STD_QUANTITY") and raw.get("STD_UNIT"):
            quantity_mt, unit_status = convert_to_mt(
                raw.get("STD_QUANTITY"), raw.get("STD_UNIT"), hct_name
            )

        # Step 5: Normalize to FOB USD
        origin_port = raw.get("ORIGIN_PORT") or raw.get("FOREIGN_PORT")
        dest_port = raw.get("DESTINATION_PORT") or raw.get("INDIAN_PORT")
        freight_used = None
        insurance_used = None
        port_charges_used = None

        if incoterm == "FOB" and price_usd is not None:
            fob_usd = price_usd
            fob_source = "direct_fob"
        elif incoterm == "CIF" and price_usd is not None:
            freight_used = lookup_freight(origin_port, dest_port)
            insurance_used = calc_insurance(price_usd, origin_port, dest_port)
            port_charges_used = lookup_port_charges(dest_port)

            deductions = (freight_used or 0) + insurance_used + port_charges_used
            # Scale freight from per-MT to total if we have quantity
            if freight_used and quantity_mt and quantity_mt > 0:
                freight_total = freight_used * quantity_mt
                port_total = port_charges_used * quantity_mt
                deductions = freight_total + insurance_used + port_total

            fob_usd = max(price_usd - deductions, 0)
            fob_source = "derived_from_cif"
        else:
            fob_usd = price_usd
            fob_source = "assumed_unknown_basis"

        # Step 6: Unit price
        fob_per_mt = None
        if fob_usd is not None and quantity_mt and quantity_mt > 0:
            fob_per_mt = fob_usd / quantity_mt

        # Step 7: Quality inference
        product_text = raw.get("PRODUCT") or raw.get("PRODUCT_DESCRIPTION") or ""
        quality = parse_quality(product_text, hct_id)

        # Step 8: Price status
        price_status = "NORMAL"
        if fob_usd is None or fob_usd == 0:
            price_status = "MISSING"
        elif fob_per_mt is not None and fob_per_mt < 10:
            price_status = "SUSPECT_LOW"
        elif fob_per_mt is not None and fob_per_mt > 50000:
            price_status = "SUSPECT_HIGH"

        # Extract date
        trade_date = raw.get("DATE") or raw.get("EXP_DATE")

        return {
            # Identifiers
            "record_id": raw.get("RECORD_ID"),
            "declaration_no": raw.get("DECLARATION_NO"),
            "bill_no": raw.get("BILL_NO"),
            # Temporal
            "trade_date": trade_date,
            "trade_type": trade_type,
            "trade_country": trade_country,
            # Parties
            "consignee": raw.get("CONSIGNEE") or raw.get("BUYER_NAME"),
            "consignor": raw.get("CONSIGNOR") or raw.get("EXPORTER_NAME"),
            # Location
            "origin_country": raw.get("ORIGIN_COUNTRY"),
            "origin_port": origin_port,
            "destination_country": raw.get("DESTINATION_COUNTRY"),
            "destination_port": dest_port,
            # Commodity
            "hs_code": hs_code,
            "hs_code_2": raw.get("HS_CODE_2") or hs_code[:2] if hs_code else None,
            "hs_code_4": raw.get("HS_CODE_4") or hs_code[:4] if hs_code else None,
            "hct_id": hct_id,
            "hct_name": hct_name,
            "hct_group": hct_group,
            "product_description": product_text,
            # Quantity
            "quantity_mt": quantity_mt,
            "quantity_original": raw.get("QUANTITY"),
            "unit_original": raw.get("UNIT"),
            "unit_status": unit_status,
            # Price
            "fob_usd_total": fob_usd,
            "fob_usd_per_mt": fob_per_mt,
            "declared_incoterm": incoterm,
            "price_source": fob_source,
            "price_status": price_status,
            "currency_original": raw.get("CURRENCY"),
            # Quality
            "quality_estimate": quality,
            # Normalization metadata
            "freight_deducted": freight_used,
            "insurance_deducted": insurance_used,
            "port_charges_deducted": port_charges_used,
            "normalized_at": datetime.utcnow().isoformat(),
            "normalization_version": "1.0",
        }

    def _extract_price(self, raw: dict, trade_country: str) -> tuple[float | None, str]:
        """Extract the best available USD price from a raw record.

        Priority:
        1. FOB_USD (Indian exports)
        2. UNIT_PRICE_USD × QUANTITY
        3. TOTAL_VALUE_USD
        4. FOB_INR / exchange rate
        5. TOTAL_VALUE_LC / FX
        """
        # Try FOB USD directly (Indian exports)
        fob_usd = raw.get("FOB_USD")
        if fob_usd and float(fob_usd) > 0:
            return float(fob_usd), "FOB_USD"

        # Try total value USD
        total_usd = raw.get("TOTAL_VALUE_USD")
        if total_usd and float(total_usd) > 0:
            return float(total_usd), "TOTAL_VALUE_USD"

        # Try unit price USD × quantity
        unit_usd = raw.get("UNIT_PRICE_USD")
        qty = raw.get("QUANTITY")
        if unit_usd and qty and float(unit_usd) > 0 and float(qty) > 0:
            return float(unit_usd) * float(qty), "UNIT_PRICE_x_QTY"

        # Try FOB INR with exchange rate
        fob_inr = raw.get("FOB_INR")
        fx_rate = raw.get("USD_EXCHANGE_RATE")
        if fob_inr and fx_rate and float(fob_inr) > 0 and float(fx_rate) > 0:
            return float(fob_inr) / float(fx_rate), "FOB_INR_converted"

        # Try item rate
        item_rate_inr = raw.get("ITEM_RATE_INR") or raw.get("STD_ITEM_RATE_INR")
        if item_rate_inr and qty and fx_rate and float(item_rate_inr) > 0:
            return (float(item_rate_inr) * float(qty)) / float(fx_rate), "ITEM_RATE_INR_converted"

        # Try local currency
        total_lc = raw.get("TOTAL_VALUE_LC")
        if total_lc and float(total_lc) > 0 and fx_rate and float(fx_rate) > 0:
            return float(total_lc) / float(fx_rate), "TOTAL_VALUE_LC_converted"

        return None, "MISSING"
