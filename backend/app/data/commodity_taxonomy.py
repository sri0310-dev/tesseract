"""Hectar Commodity Taxonomy (HCT) — the unified classification system.

Maps HS codes from any country to Hectar's internal commodity identifiers,
enabling apples-to-apples comparison of the same product across different
customs regimes.
"""

TAXONOMY: dict[str, dict] = {
    "HCT-0801-RCN-INSHELL": {
        "hct_name": "Raw Cashew Nuts (In Shell)",
        "hct_group": "Cashew Complex",
        "hct_supergroup": "Tree Nuts",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "080131", "confidence": "HIGH"},
            {"country": "INDIA", "hs_code": "08013110", "confidence": "HIGH"},
            {"country": "INDIA", "hs_code": "08013120", "confidence": "HIGH"},
            {"country": "VIETNAM", "hs_code": "08013100", "confidence": "HIGH"},
            {"country": "IVORY COAST", "hs_code": "080131", "confidence": "HIGH"},
        ],
        "quality_grades": [
            "Grade A (180+ nuts/kg)",
            "Grade B (180-210)",
            "Grade C (210+)",
        ],
    },
    "HCT-0801-CASHEW-KERNEL": {
        "hct_name": "Cashew Kernels (Processed)",
        "hct_group": "Cashew Complex",
        "hct_supergroup": "Tree Nuts",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "080132", "confidence": "HIGH"},
            {"country": "INDIA", "hs_code": "08013200", "confidence": "HIGH"},
            {"country": "VIETNAM", "hs_code": "08013200", "confidence": "HIGH"},
        ],
        "quality_grades": ["W180", "W210", "W240", "W320", "W450", "SW", "LWP", "SWP"],
    },
    "HCT-1207-SESAME": {
        "hct_name": "Sesame Seeds",
        "hct_group": "Sesame",
        "hct_supergroup": "Oilseeds",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "120740", "confidence": "HIGH"},
            {"country": "INDIA", "hs_code": "12074000", "confidence": "HIGH"},
            {"country": "ETHIOPIA", "hs_code": "120740", "confidence": "HIGH"},
            {"country": "NIGERIA", "hs_code": "120740", "confidence": "HIGH"},
        ],
        "quality_grades": [
            "Hulled 99.95%",
            "Hulled 99.90%",
            "Natural (unhulled)",
            "Mixed",
        ],
    },
    "HCT-1006-RICE-NONBASMATI": {
        "hct_name": "Rice (Non-Basmati)",
        "hct_group": "Rice",
        "hct_supergroup": "Grains & Cereals",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "1006", "confidence": "MEDIUM"},
            {"country": "INDIA", "hs_code": "10063010", "confidence": "HIGH"},
            {"country": "INDIA", "hs_code": "10063090", "confidence": "HIGH"},
            {"country": "VIETNAM", "hs_code": "100630", "confidence": "HIGH"},
            {"country": "THAILAND", "hs_code": "100630", "confidence": "HIGH"},
        ],
        "quality_grades": [
            "5% Broken",
            "10% Broken",
            "15% Broken",
            "25% Broken",
            "100% Broken",
            "Parboiled",
            "Long Grain White",
        ],
    },
    "HCT-1006-RICE-BASMATI": {
        "hct_name": "Basmati Rice",
        "hct_group": "Rice",
        "hct_supergroup": "Grains & Cereals",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "INDIA", "hs_code": "10063020", "confidence": "HIGH"},
            {"country": "PAKISTAN", "hs_code": "100630", "confidence": "MEDIUM"},
        ],
        "quality_grades": ["1121 Sella", "1121 Steam", "Sugandha", "Pusa", "Traditional"],
    },
    "HCT-1201-SOYBEAN": {
        "hct_name": "Soybeans",
        "hct_group": "Soybeans",
        "hct_supergroup": "Oilseeds",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "120190", "confidence": "HIGH"},
            {"country": "NIGERIA", "hs_code": "12019000", "confidence": "HIGH"},
            {"country": "INDIA", "hs_code": "12019000", "confidence": "HIGH"},
        ],
        "quality_grades": ["Grade 1", "Grade 2", "Feed Grade"],
    },
    "HCT-1801-COCOA": {
        "hct_name": "Cocoa Beans",
        "hct_group": "Cocoa",
        "hct_supergroup": "Cocoa",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "180100", "confidence": "HIGH"},
        ],
        "quality_grades": ["Grade I", "Grade II", "Sub-Grade"],
    },
    "HCT-1207-SHEA": {
        "hct_name": "Shea Nuts/Butter",
        "hct_group": "Shea",
        "hct_supergroup": "Oilseeds",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "120799", "confidence": "MEDIUM"},
        ],
        "quality_grades": ["Nuts", "Crude Butter", "Refined Butter"],
    },
    "HCT-1511-PALMOIL": {
        "hct_name": "Palm Oil",
        "hct_group": "Palm Oil",
        "hct_supergroup": "Vegetable Oils",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "151110", "confidence": "HIGH"},
            {"country": "*", "hs_code": "151190", "confidence": "HIGH"},
        ],
        "quality_grades": ["Crude (CPO)", "Refined (RPO)", "Olein", "Stearin"],
    },
    "HCT-5201-COTTON": {
        "hct_name": "Raw Cotton",
        "hct_group": "Cotton",
        "hct_supergroup": "Cotton",
        "standard_unit": "MT",
        "hs_mappings": [
            {"country": "*", "hs_code": "520100", "confidence": "HIGH"},
        ],
        "quality_grades": ["S-6", "J-34", "MCU-5", "Shankar-6", "CIS"],
    },
}


def classify_by_hs_code(hs_code: str, country: str = "*") -> dict | None:
    """Resolve an HS code to an HCT commodity entry.

    Tries country-specific match first, then falls back to wildcard.
    Matches from most specific (8 digits) to least (2 digits).
    """
    hs_code = str(hs_code).strip()

    for hct_id, entry in TAXONOMY.items():
        for mapping in entry["hs_mappings"]:
            map_hs = str(mapping["hs_code"])
            map_country = mapping["country"]

            if map_country == country and hs_code.startswith(map_hs):
                return {"hct_id": hct_id, **entry, "match_confidence": mapping["confidence"]}

    # Wildcard fallback
    for hct_id, entry in TAXONOMY.items():
        for mapping in entry["hs_mappings"]:
            map_hs = str(mapping["hs_code"])
            if mapping["country"] == "*" and hs_code.startswith(map_hs):
                return {"hct_id": hct_id, **entry, "match_confidence": mapping["confidence"]}

    return None
