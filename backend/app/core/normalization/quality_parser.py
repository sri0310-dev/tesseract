"""Commodity-specific product description parsers.

Extracts quality, grade, variety, and processing state from
the free-text PRODUCT / PRODUCT_DESCRIPTION fields that customs
data provides. This is where opaque commodities reveal their
true character.
"""

import re


def parse_quality(product_text: str | None, hct_id: str | None = None) -> dict:
    """Parse product description into structured quality attributes.

    Returns a dict with:
    - grade: inferred quality grade
    - confidence: 0-1 score
    - signals_used: list of detection methods that fired
    - details: human-readable summary
    """
    if not product_text:
        return {"grade": "Unknown", "confidence": 0.0, "signals_used": [], "details": "No description"}

    text = product_text.upper().strip()
    result = {"grade": "Standard", "confidence": 0.3, "signals_used": [], "details": ""}

    if hct_id and "RCN" in hct_id:
        return _parse_cashew(text)
    elif hct_id and "KERNEL" in (hct_id or ""):
        return _parse_cashew_kernel(text)
    elif hct_id and "SESAME" in (hct_id or ""):
        return _parse_sesame(text)
    elif hct_id and "RICE" in (hct_id or ""):
        return _parse_rice(text)
    elif hct_id and "SOYBEAN" in (hct_id or ""):
        return _parse_soybean(text)

    return result


def _parse_cashew(text: str) -> dict:
    signals = []
    grade = "Standard"
    details_parts = []

    # State detection
    state = "raw_in_shell"
    if "KERNEL" in text or any(g in text for g in ["W180", "W240", "W320", "W450"]):
        state = "kernel"
    elif "SHELLED" in text:
        state = "shelled"
    details_parts.append(f"state={state}")

    # Outturn (KOR) — critical quality indicator
    outturn_match = re.search(r'OUTTURN\s*[:\-]?\s*(\d+\.?\d*)\s*(?:LBS|#)?', text)
    if outturn_match:
        outturn = float(outturn_match.group(1))
        signals.append("outturn_detected")
        details_parts.append(f"outturn={outturn} lbs")
        if outturn >= 48:
            grade = "Premium"
        elif outturn >= 44:
            grade = "Grade A"
        else:
            grade = "Grade B"

    # Nut count per kg
    nut_count_match = re.search(r'(\d+)\s*(?:NUTS?|NUT)\s*/?\s*KG', text)
    if nut_count_match:
        count = int(nut_count_match.group(1))
        signals.append("nut_count_detected")
        details_parts.append(f"nut_count={count}/kg")

    # Origin claims
    for origin in ["IVORY COAST", "GHANA", "NIGERIA", "TANZANIA", "MOZAMBIQUE",
                    "GUINEA BISSAU", "BENIN", "COTE D'IVOIRE"]:
        if origin in text:
            signals.append("origin_claim")
            details_parts.append(f"origin={origin}")
            break

    conf = min(0.3 + len(signals) * 0.2, 0.95)
    return {"grade": grade, "confidence": conf, "signals_used": signals,
            "details": "; ".join(details_parts)}


def _parse_cashew_kernel(text: str) -> dict:
    signals = []
    grade = "Standard"
    details_parts = []

    grade_match = re.search(r'(W\s?180|W\s?210|W\s?240|W\s?320|W\s?450|WW\d+|SW\d+|LWP|SWP|BB|SS)', text)
    if grade_match:
        grade = grade_match.group(1).replace(" ", "")
        signals.append("kernel_grade_detected")
        details_parts.append(f"grade={grade}")

    if "SCORCHED" in text:
        signals.append("processing_note")
        details_parts.append("scorched")
    if "DESSERT" in text:
        signals.append("processing_note")
        details_parts.append("dessert")

    conf = min(0.4 + len(signals) * 0.25, 0.95)
    return {"grade": grade, "confidence": conf, "signals_used": signals,
            "details": "; ".join(details_parts)}


def _parse_sesame(text: str) -> dict:
    signals = []
    grade = "Standard"
    details_parts = []

    # Purity
    purity_match = re.search(r'(\d{2}\.?\d*)\s*%\s*(?:PURITY|PURE)', text)
    if purity_match:
        purity = float(purity_match.group(1))
        signals.append("purity_detected")
        details_parts.append(f"purity={purity}%")
        if purity >= 99.95:
            grade = "Premium Hulled"
        elif purity >= 99.90:
            grade = "Hulled"

    # Processing state
    if "HULLED" in text:
        signals.append("processing_state")
        details_parts.append("hulled")
        if grade == "Standard":
            grade = "Hulled"
    elif "NATURAL" in text or "UNHULLED" in text:
        signals.append("processing_state")
        details_parts.append("natural/unhulled")
        grade = "Natural"

    # Aflatoxin
    if "AFLATOXIN" in text and "FREE" in text:
        signals.append("quality_certification")
        details_parts.append("aflatoxin-free")

    # Color
    for color in ["WHITE", "BLACK", "BROWN", "MIXED"]:
        if color in text:
            signals.append("color_detected")
            details_parts.append(f"color={color.lower()}")
            break

    conf = min(0.3 + len(signals) * 0.2, 0.95)
    return {"grade": grade, "confidence": conf, "signals_used": signals,
            "details": "; ".join(details_parts)}


def _parse_rice(text: str) -> dict:
    signals = []
    grade = "Standard"
    details_parts = []

    # Broken percentage
    broken_match = re.search(r'(\d+)\s*%?\s*(?:BROKEN|BRKN|PCT)', text)
    if broken_match:
        pct = int(broken_match.group(1))
        signals.append("broken_pct_detected")
        details_parts.append(f"broken={pct}%")
        if pct <= 5:
            grade = "5% Broken (Premium)"
        elif pct <= 15:
            grade = f"{pct}% Broken (Mid)"
        elif pct <= 25:
            grade = "25% Broken (Standard)"
        else:
            grade = "100% Broken (Value)"

    # Basmati
    if "BASMATI" in text:
        grade = "Basmati"
        signals.append("variety_detected")
        if "1121" in text:
            details_parts.append("variety=1121")
        if "SELLA" in text:
            details_parts.append("processing=sella/parboiled")
        if "STEAM" in text:
            details_parts.append("processing=steamed")

    # Long grain / parboiled
    if "LONG GRAIN" in text:
        signals.append("type_detected")
        details_parts.append("long grain")
    if "PARBOILED" in text and "BASMATI" not in text:
        signals.append("processing_detected")
        details_parts.append("parboiled")

    # Indian varieties
    for var in ["PONNI", "SONA MASURI", "SONA MASOORI", "SUGANDHA", "PUSA"]:
        if var in text:
            signals.append("variety_detected")
            details_parts.append(f"variety={var}")
            break

    conf = min(0.3 + len(signals) * 0.2, 0.95)
    return {"grade": grade, "confidence": conf, "signals_used": signals,
            "details": "; ".join(details_parts)}


def _parse_soybean(text: str) -> dict:
    signals = []
    grade = "Standard"
    details_parts = []

    if "FEED" in text:
        grade = "Feed Grade"
        signals.append("grade_detected")
        details_parts.append("feed grade")

    if "NON-GMO" in text or "NON GMO" in text:
        signals.append("gmo_status")
        details_parts.append("non-GMO")

    # Protein content
    protein_match = re.search(r'(\d+\.?\d*)\s*%?\s*PROTEIN', text)
    if protein_match:
        prot = float(protein_match.group(1))
        signals.append("protein_detected")
        details_parts.append(f"protein={prot}%")

    # Moisture
    moisture_match = re.search(r'(\d+\.?\d*)\s*%?\s*MOISTURE', text)
    if moisture_match:
        moist = float(moisture_match.group(1))
        signals.append("moisture_detected")
        details_parts.append(f"moisture={moist}%")

    conf = min(0.3 + len(signals) * 0.2, 0.95)
    return {"grade": grade, "confidence": conf, "signals_used": signals,
            "details": "; ".join(details_parts)}
