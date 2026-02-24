"""Normalization pipeline — the core competitive moat.

Transforms raw Eximpedia trade records into comparable, standardized
records with FOB USD pricing, metric tonne quantities, and quality
grades. Every single record flows through this before it reaches
the intelligence layer.

Field name mapping (Eximpedia varies by trade type/country):

IMPORT (India):
  IMPORTER_NAME, SUPPLIER_NAME, IMP_DATE, INDIAN_PORT (dest),
  PORT_OF_SHIPMENT (origin), ORIGIN_COUNTRY, HS_CODE (int),
  QUANTITY, UNIT, STD_QUANTITY, STD_UNIT, STD_UNIT_PRICE_USD,
  TOTAL_ASSESS_USD, TOTAL_ASSESSABLE_VALUE_INR, UNIT_PRICE_USD

EXPORT (India):
  EXPORTER_NAME, BUYER_NAME, EXP_DATE, INDIAN_PORT (origin),
  FOREIGN_PORT (dest), COUNTRY (dest), HS_CODE (int),
  QUANTITY, UNIT, STD_QUANTITY, STD_UNIT, FOB_USD, FOB_INR,
  ITEM_RATE_INR, USD_EXCHANGE_RATE
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
        """Normalize a single raw record from Eximpedia."""
        trade_type = trade_type.upper()
        trade_country = trade_country.upper()
        is_export = trade_type == "EXPORT"

        # Step 1: Incoterm basis
        incoterm = infer_incoterm(trade_type, trade_country)

        # Step 2: Price extraction
        price_usd, price_source = self._extract_price(raw, trade_country)

        # Step 3: Commodity classification
        # Eximpedia returns HS_CODE as integer (e.g. 8013100) — convert to string
        raw_hs = raw.get("HS_CODE", "")
        hs_code = str(raw_hs).strip() if raw_hs else ""
        # Eximpedia returns HS codes as integers, stripping leading zeros
        # Standard HS codes are 6 or 8 digits (chapters 01-09 need a leading zero)
        # e.g., 8013100 → "08013100", 12074090 → "12074090"
        if hs_code and hs_code.isdigit():
            if len(hs_code) < 8 and len(hs_code) % 2 == 1:
                hs_code = "0" + hs_code  # Restore leading zero

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

        # Step 5: Determine ports based on trade direction
        # For Indian imports: INDIAN_PORT = destination, PORT_OF_SHIPMENT = origin
        # For Indian exports: INDIAN_PORT = origin, FOREIGN_PORT = destination
        if is_export:
            origin_port = raw.get("INDIAN_PORT")
            dest_port = raw.get("FOREIGN_PORT")
        else:
            origin_port = raw.get("PORT_OF_SHIPMENT") or raw.get("FOREIGN_PORT")
            dest_port = raw.get("INDIAN_PORT")

        # Step 6: Normalize to FOB USD
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
            if freight_used and quantity_mt and quantity_mt > 0:
                freight_total = freight_used * quantity_mt
                port_total = port_charges_used * quantity_mt
                deductions = freight_total + insurance_used + port_total

            fob_usd = max(price_usd - deductions, 0)
            fob_source = "derived_from_cif"
        else:
            fob_usd = price_usd
            fob_source = "assumed_unknown_basis"

        # Step 7: Unit price
        fob_per_mt = None
        if fob_usd is not None and quantity_mt and quantity_mt > 0:
            fob_per_mt = fob_usd / quantity_mt

        # Step 8: Quality inference
        product_text = raw.get("PRODUCT_DESCRIPTION") or raw.get("PRODUCT") or ""
        quality = parse_quality(product_text, hct_id)

        # Step 9: Price status
        price_status = "NORMAL"
        if fob_usd is None or fob_usd == 0:
            price_status = "MISSING"
        elif fob_per_mt is not None and fob_per_mt < 10:
            price_status = "SUSPECT_LOW"
        elif fob_per_mt is not None and fob_per_mt > 50000:
            price_status = "SUSPECT_HIGH"

        # Extract date — Eximpedia uses IMP_DATE for imports, EXP_DATE for exports
        trade_date = raw.get("IMP_DATE") or raw.get("EXP_DATE") or raw.get("DATE")
        # Normalize date string: "2026-01-31T00:00:00.0000000Z" → "2026-01-31"
        if trade_date and isinstance(trade_date, str) and "T" in trade_date:
            trade_date = trade_date[:10]

        # Determine origin/destination country
        if is_export:
            origin_country = trade_country
            destination_country = raw.get("COUNTRY") or raw.get("DESTINATION_COUNTRY")
        else:
            origin_country = raw.get("ORIGIN_COUNTRY")
            destination_country = trade_country

        # Determine buyer/seller
        if is_export:
            consignee = raw.get("BUYER_NAME") or raw.get("STD_BUYER_NAME")
            consignor = raw.get("EXPORTER_NAME")
        else:
            consignee = raw.get("IMPORTER_NAME")
            consignor = raw.get("SUPPLIER_NAME") or raw.get("UPDATED_SUPPLIER_NAME")

        return {
            # Identifiers
            "record_id": raw.get("DECLARATION_NO"),
            "declaration_no": raw.get("DECLARATION_NO"),
            "bill_no": raw.get("BILL_NO"),
            # Temporal
            "trade_date": trade_date,
            "trade_type": trade_type,
            "trade_country": trade_country,
            # Parties
            "consignee": consignee,
            "consignor": consignor,
            # Location
            "origin_country": origin_country,
            "origin_port": origin_port,
            "destination_country": destination_country,
            "destination_port": dest_port,
            # Commodity
            "hs_code": hs_code,
            "hs_code_2": raw.get("HS_CODE_2") or (hs_code[:2] if hs_code else None),
            "hs_code_4": raw.get("HS_CODE_4") or (hs_code[:4] if hs_code else None),
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
            "currency_original": raw.get("CURRENCY") or raw.get("INVOICE_CURRENCY"),
            # Quality
            "quality_estimate": quality,
            # Normalization metadata
            "freight_deducted": freight_used,
            "insurance_deducted": insurance_used,
            "port_charges_deducted": port_charges_used,
            "normalized_at": datetime.utcnow().isoformat(),
            "normalization_version": "1.1",
        }

    def _extract_price(self, raw: dict, trade_country: str) -> tuple[float | None, str]:
        """Extract the best available USD price from a raw record.

        Priority:
        1. FOB_USD (Indian exports)
        2. TOTAL_ASSESS_USD (Indian imports)
        3. STD_UNIT_PRICE_USD × STD_QUANTITY
        4. UNIT_PRICE_USD × QUANTITY
        5. FOB_INR / exchange rate
        6. ITEM_RATE_INR × QUANTITY / exchange rate
        7. TOTAL_ASSESSABLE_VALUE_INR / exchange rate
        """
        # Try FOB USD directly (Indian exports)
        fob_usd = raw.get("FOB_USD")
        if fob_usd is not None:
            try:
                val = float(fob_usd)
                if val > 0:
                    return val, "FOB_USD"
            except (ValueError, TypeError):
                pass

        # Try total assessable USD (Indian imports)
        total_usd = raw.get("TOTAL_ASSESS_USD") or raw.get("TOTAL_VALUE_USD")
        if total_usd is not None:
            try:
                val = float(total_usd)
                if val > 0:
                    return val, "TOTAL_ASSESS_USD"
            except (ValueError, TypeError):
                pass

        # Try STD_UNIT_PRICE_USD × STD_QUANTITY
        std_unit_usd = raw.get("STD_UNIT_PRICE_USD")
        std_qty = raw.get("STD_QUANTITY")
        if std_unit_usd is not None and std_qty is not None:
            try:
                val = float(std_unit_usd) * float(std_qty)
                if val > 0:
                    return val, "STD_UNIT_PRICE_x_QTY"
            except (ValueError, TypeError):
                pass

        # Try unit price USD × quantity
        unit_usd = raw.get("UNIT_PRICE_USD")
        qty = raw.get("QUANTITY")
        if unit_usd is not None and qty is not None:
            try:
                val = float(unit_usd) * float(qty)
                if val > 0:
                    return val, "UNIT_PRICE_x_QTY"
            except (ValueError, TypeError):
                pass

        # Try FOB INR with exchange rate
        fob_inr = raw.get("FOB_INR")
        fx_rate = raw.get("USD_EXCHANGE_RATE")
        if fob_inr is not None and fx_rate is not None:
            try:
                val = float(fob_inr) / float(fx_rate)
                if val > 0:
                    return val, "FOB_INR_converted"
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # Try item rate INR
        item_rate_inr = raw.get("ITEM_RATE_INR") or raw.get("STD_ITEM_RATE_INR")
        if item_rate_inr is not None and qty is not None and fx_rate is not None:
            try:
                val = (float(item_rate_inr) * float(qty)) / float(fx_rate)
                if val > 0:
                    return val, "ITEM_RATE_INR_converted"
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # Try assessable value INR
        assess_inr = raw.get("TOTAL_ASSESSABLE_VALUE_INR")
        if assess_inr is not None and fx_rate is not None:
            try:
                val = float(assess_inr) / float(fx_rate)
                if val > 0:
                    return val, "TOTAL_ASSESSABLE_VALUE_INR_converted"
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        return None, "MISSING"
