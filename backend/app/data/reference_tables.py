"""Reference data tables for normalization: freight rates, port charges,
insurance rates, FX, unit conversions, and seasonal patterns.
"""

# ── Freight Rate Reference (USD per MT) ──────────────────────────
FREIGHT_RATES: list[dict] = [
    {"route_id": "ABIDJAN-TUTICORIN", "origin_port": "ABIDJAN", "destination_port": "TUTICORIN",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 42.50, "currency": "USD"},
    {"route_id": "ABIDJAN-MANGALORE", "origin_port": "ABIDJAN", "destination_port": "MANGALORE",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 44.00, "currency": "USD"},
    {"route_id": "TEMA-TUTICORIN", "origin_port": "TEMA", "destination_port": "TUTICORIN",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 40.00, "currency": "USD"},
    {"route_id": "LAGOS-TUTICORIN", "origin_port": "LAGOS", "destination_port": "TUTICORIN",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 45.00, "currency": "USD"},
    {"route_id": "DAR-TUTICORIN", "origin_port": "DAR ES SALAAM", "destination_port": "TUTICORIN",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 35.00, "currency": "USD"},
    {"route_id": "ABIDJAN-HOCHIMINH", "origin_port": "ABIDJAN", "destination_port": "HO CHI MINH",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 55.00, "currency": "USD"},
    {"route_id": "TEMA-HOCHIMINH", "origin_port": "TEMA", "destination_port": "HO CHI MINH",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 53.00, "currency": "USD"},
    {"route_id": "DJIBOUTI-KANDLA", "origin_port": "DJIBOUTI", "destination_port": "KANDLA",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 28.00, "currency": "USD"},
    {"route_id": "LAGOS-TIANJIN", "origin_port": "LAGOS", "destination_port": "TIANJIN",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 60.00, "currency": "USD"},
    {"route_id": "LAGOS-QINGDAO", "origin_port": "LAGOS", "destination_port": "QINGDAO",
     "vessel_class": "HANDYSIZE", "rate_per_mt": 58.00, "currency": "USD"},
    {"route_id": "KAKINADA-LAGOS", "origin_port": "KAKINADA", "destination_port": "LAGOS",
     "vessel_class": "SUPRAMAX", "rate_per_mt": 48.00, "currency": "USD"},
    {"route_id": "KANDLA-LAGOS", "origin_port": "KANDLA", "destination_port": "LAGOS",
     "vessel_class": "SUPRAMAX", "rate_per_mt": 46.00, "currency": "USD"},
    {"route_id": "KAKINADA-TEMA", "origin_port": "KAKINADA", "destination_port": "TEMA",
     "vessel_class": "SUPRAMAX", "rate_per_mt": 47.00, "currency": "USD"},
]


def lookup_freight(origin_port: str | None, dest_port: str | None) -> float | None:
    """Find freight rate for a port pair. Returns USD/MT or None."""
    if not origin_port or not dest_port:
        return None
    o = origin_port.upper().strip()
    d = dest_port.upper().strip()
    for entry in FREIGHT_RATES:
        if entry["origin_port"] in o and entry["destination_port"] in d:
            return entry["rate_per_mt"]
        if o in entry["origin_port"] and d in entry["destination_port"]:
            return entry["rate_per_mt"]
    return None


# ── Insurance Rates (% of cargo value) ───────────────────────────
INSURANCE_RATES: dict[str, dict] = {
    "standard": {"rate_pct": 0.0015, "war_risk_pct": 0.0},
    "gulf_of_guinea": {"rate_pct": 0.0015, "war_risk_pct": 0.0025},
    "red_sea": {"rate_pct": 0.0015, "war_risk_pct": 0.005},
}

HIGH_RISK_PORTS = {
    "gulf_of_guinea": ["LAGOS", "APAPA", "TEMA", "ABIDJAN", "LOME", "COTONOU"],
    "red_sea": ["ADEN", "HODEIDAH", "DJIBOUTI", "PORT SUDAN"],
}


def calc_insurance(cargo_value_usd: float, origin_port: str | None = None,
                   dest_port: str | None = None) -> float:
    """Calculate insurance cost in USD."""
    risk_profile = "standard"
    for port in [origin_port or "", dest_port or ""]:
        port_upper = port.upper()
        for risk_key, ports in HIGH_RISK_PORTS.items():
            if any(p in port_upper for p in ports):
                risk_profile = risk_key
                break

    rates = INSURANCE_RATES[risk_profile]
    total_rate = rates["rate_pct"] + rates["war_risk_pct"]
    return cargo_value_usd * total_rate


# ── Port Charges (USD per MT) ────────────────────────────────────
PORT_CHARGES: dict[str, float] = {
    "TUTICORIN": 4.70,
    "MANGALORE": 4.20,
    "KOCHI": 4.50,
    "KANDLA": 3.80,
    "MUMBAI": 5.20,
    "CHENNAI": 4.80,
    "KAKINADA": 3.50,
    "KRISHNAPATNAM": 3.80,
    "HO CHI MINH": 5.00,
    "HAI PHONG": 4.50,
    "LAGOS": 8.50,
    "APAPA": 8.50,
    "TEMA": 6.00,
    "ABIDJAN": 5.50,
    "DAR ES SALAAM": 6.50,
    "DJIBOUTI": 7.00,
    "TIANJIN": 4.00,
    "QINGDAO": 3.80,
    "SHANGHAI": 3.50,
}


def lookup_port_charges(port: str | None) -> float:
    """Get total port charges for a port in USD/MT."""
    if not port:
        return 0.0
    p = port.upper().strip()
    for port_name, charge in PORT_CHARGES.items():
        if port_name in p or p in port_name:
            return charge
    return 4.0  # Conservative default


# ── Unit Conversion ──────────────────────────────────────────────
UNIT_CONVERSIONS: dict[str, float | None] = {
    "KGS": 0.001,
    "KG": 0.001,
    "MTS": 1.0,
    "MT": 1.0,
    "TON": 1.0,
    "TONS": 1.0,
    "TONNE": 1.0,
    "TONNES": 1.0,
    "LONG TON": 1.01605,
    "SHORT TON": 0.907185,
    "LBS": 0.000453592,
    "QUINTAL": 0.1,
    "QTL": 0.1,
}

COMMODITY_UNIT_CONVERSIONS: dict[str, dict] = {
    "cashew_bags": {"bag_weight_kg": 80, "to_MT": 0.08},
    "rice_bags": {"bag_weight_kg": 50, "to_MT": 0.05},
    "cocoa_bags": {"bag_weight_kg": 60, "to_MT": 0.06},
    "cotton_bales": {"bale_weight_kg": 170, "to_MT": 0.17},
    "palm_oil_litre": {"density_kg_per_l": 0.92, "to_MT": 0.00092},
}


def convert_to_mt(quantity: float | None, unit: str | None,
                  commodity_hint: str | None = None) -> tuple[float | None, str]:
    """Convert a quantity to metric tonnes.

    Returns (quantity_mt, status) where status is one of:
    - "OK": converted successfully
    - "ASSUMED_KG": unit was missing, assumed KG based on magnitude
    - "UNRESOLVABLE": cannot determine conversion
    """
    if quantity is None or quantity <= 0:
        return None, "MISSING"

    if unit is None:
        # Heuristic: if quantity > 10000, probably KG; if < 100, probably MT
        if quantity > 5000:
            return quantity * 0.001, "ASSUMED_KG"
        elif quantity < 200:
            return quantity, "ASSUMED_MT"
        return None, "UNRESOLVABLE"

    unit_upper = unit.upper().strip()

    # Direct conversion
    if unit_upper in UNIT_CONVERSIONS:
        factor = UNIT_CONVERSIONS[unit_upper]
        if factor is not None:
            return quantity * factor, "OK"

    # Commodity-specific
    if unit_upper in ("BAGS", "BAG"):
        if commodity_hint and "cashew" in commodity_hint.lower():
            return quantity * 0.08, "OK"
        elif commodity_hint and "rice" in commodity_hint.lower():
            return quantity * 0.05, "OK"
        elif commodity_hint and "cocoa" in commodity_hint.lower():
            return quantity * 0.06, "OK"
        return quantity * 0.05, "ASSUMED_BAG_WEIGHT"

    if unit_upper == "NOS" or unit_upper == "PCS":
        return None, "UNRESOLVABLE"

    return None, "UNRESOLVABLE"


# ── Incoterm Map ─────────────────────────────────────────────────
INCOTERM_MAP: dict[tuple[str, str], str] = {
    ("EXPORT", "INDIA"): "FOB",
    ("IMPORT", "INDIA"): "CIF",
    ("EXPORT", "BRAZIL"): "FOB",
    ("IMPORT", "BANGLADESH"): "CIF",
    ("IMPORT", "VIETNAM"): "CIF",
    ("EXPORT", "VIETNAM"): "FOB",
    ("IMPORT", "NIGERIA"): "CIF",
    ("EXPORT", "NIGERIA"): "FOB",
    ("EXPORT", "ETHIOPIA"): "FOB",
    ("EXPORT", "IVORY COAST"): "FOB",
    ("EXPORT", "GHANA"): "FOB",
    ("EXPORT", "TANZANIA"): "FOB",
    ("IMPORT", "USA"): "CIF",
    ("IMPORT", "INDONESIA"): "CIF",
    ("EXPORT", "INDONESIA"): "FOB",
    ("IMPORT", "PAKISTAN"): "CIF",
    ("EXPORT", "PAKISTAN"): "FOB",
    ("IMPORT", "SRI LANKA"): "CIF",
    ("IMPORT", "KENYA"): "CIF",
    ("IMPORT", "MEXICO"): "CIF",
    ("EXPORT", "MEXICO"): "FOB",
    ("IMPORT", "ARGENTINA"): "CIF",
    ("EXPORT", "ARGENTINA"): "FOB",
    ("IMPORT", "COLOMBIA"): "CIF",
    ("EXPORT", "COLOMBIA"): "FOB",
    ("IMPORT", "CHILE"): "CIF",
    ("EXPORT", "CHILE"): "FOB",
    ("IMPORT", "PHILIPPINES"): "CIF",
    ("EXPORT", "PERU"): "FOB",
    ("IMPORT", "TURKEY"): "CIF",
    ("EXPORT", "TURKEY"): "FOB",
    ("IMPORT", "KAZAKHSTAN"): "CIF",
    ("EXPORT", "KAZAKHSTAN"): "FOB",
    ("IMPORT", "URUGUAY"): "CIF",
    ("EXPORT", "URUGUAY"): "FOB",
    ("IMPORT", "CAMEROON"): "CIF",
    ("EXPORT", "CAMEROON"): "FOB",
}


def infer_incoterm(trade_type: str, trade_country: str) -> str:
    """Determine declared incoterm basis from trade type and country."""
    key = (trade_type.upper(), trade_country.upper())
    return INCOTERM_MAP.get(key, "FOB" if trade_type.upper() == "EXPORT" else "CIF")


# ── Seasonal Patterns ────────────────────────────────────────────
SEASONAL_PATTERNS: dict[str, dict] = {
    "HCT-0801-RCN-INSHELL": {
        "crop_years": [
            {
                "name": "West African Main Crop",
                "start_month": 2, "end_month": 7,
                "peak_months": [3, 4, 5],
                "origins": ["IVORY COAST", "GHANA", "GUINEA BISSAU", "BENIN"],
            },
            {
                "name": "East African Crop",
                "start_month": 10, "end_month": 1,
                "peak_months": [11, 12],
                "origins": ["TANZANIA", "MOZAMBIQUE"],
            },
        ],
        "monthly_weights": {
            1: 0.06, 2: 0.08, 3: 0.14, 4: 0.16, 5: 0.14,
            6: 0.10, 7: 0.07, 8: 0.05, 9: 0.04, 10: 0.05,
            11: 0.06, 12: 0.05,
        },
    },
    "HCT-1207-SESAME": {
        "crop_years": [
            {
                "name": "Sudan/Ethiopia Main",
                "start_month": 10, "end_month": 3,
                "peak_months": [11, 12, 1],
                "origins": ["SUDAN", "ETHIOPIA"],
            },
            {
                "name": "Nigeria Multi-crop",
                "start_month": 4, "end_month": 9,
                "peak_months": [6, 7, 8],
                "origins": ["NIGERIA"],
            },
            {
                "name": "India Rabi",
                "start_month": 2, "end_month": 5,
                "peak_months": [3, 4],
                "origins": ["INDIA"],
            },
        ],
        "monthly_weights": {
            1: 0.10, 2: 0.09, 3: 0.09, 4: 0.08, 5: 0.06,
            6: 0.07, 7: 0.08, 8: 0.08, 9: 0.07, 10: 0.08,
            11: 0.10, 12: 0.10,
        },
    },
    "HCT-1201-SOYBEAN": {
        "crop_years": [
            {
                "name": "Nigeria Main",
                "start_month": 10, "end_month": 3,
                "peak_months": [11, 12, 1],
                "origins": ["NIGERIA"],
            },
        ],
        "monthly_weights": {
            1: 0.10, 2: 0.09, 3: 0.08, 4: 0.07, 5: 0.06,
            6: 0.06, 7: 0.07, 8: 0.07, 9: 0.08, 10: 0.09,
            11: 0.12, 12: 0.11,
        },
    },
    "HCT-1006-RICE-NONBASMATI": {
        "crop_years": [
            {
                "name": "India Kharif",
                "start_month": 10, "end_month": 9,
                "peak_months": [1, 2, 3, 4],
                "origins": ["INDIA"],
            },
            {
                "name": "Vietnam Winter-Spring",
                "start_month": 2, "end_month": 5,
                "peak_months": [3, 4, 5],
                "origins": ["VIETNAM"],
            },
        ],
        "monthly_weights": {
            1: 0.10, 2: 0.10, 3: 0.10, 4: 0.09, 5: 0.08,
            6: 0.07, 7: 0.07, 8: 0.07, 9: 0.07, 10: 0.08,
            11: 0.08, 12: 0.09,
        },
    },
}
