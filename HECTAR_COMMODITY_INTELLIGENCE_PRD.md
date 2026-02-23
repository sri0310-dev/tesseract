# HECTAR COMMODITY FLOW INTELLIGENCE SUITE
## Product Requirements Document (PRD) — AI-Buildable Specification
### Version 1.0 | February 2026

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Data Source: Eximpedia Trade API](#3-data-source-eximpedia-trade-api)
4. [System Architecture](#4-system-architecture)
5. [Module 1: Data Ingestion Layer](#5-module-1-data-ingestion-layer)
6. [Module 2: Normalization Engine](#6-module-2-normalization-engine)
7. [Module 3: Intelligence Layer](#7-module-3-intelligence-layer)
8. [Module 4: Decision Layer (Trader UI)](#8-module-4-decision-layer-trader-ui)
9. [Priority Commodity Corridors](#9-priority-commodity-corridors)
10. [Algorithm Specifications](#10-algorithm-specifications)
11. [Ground Price Collection Integration](#11-ground-price-collection-integration)
12. [Data Model & Schema](#12-data-model--schema)
13. [API Integration Patterns](#13-api-integration-patterns)
14. [Deployment & Infrastructure](#14-deployment--infrastructure)
15. [Implementation Roadmap](#15-implementation-roadmap)
16. [Appendices](#16-appendices)

---

## 1. EXECUTIVE SUMMARY

### 1.1 What We Are Building

A predictive intelligence platform that transforms raw global customs/trade data into actionable commodity pricing signals, supply-demand intelligence, and counterparty insights. The system ingests shipment-level data from the Eximpedia Trade API (covering 80+ countries), normalizes declared values to standardized incoterm bases (primarily FOB), constructs implied daily supply-demand balance sheets, and predicts spot rate directional movements — all with a particular focus on **non-exchange-listed commodities** where pricing data is opaque, fragmented, or entirely absent from public benchmarks.

### 1.2 Why This Is Disruptive

Traditional commodity S&D analysis relies on:
- Monthly government reports (USDA WASDE, IGC, FAO) — 30-60 day lag
- Price Reporting Agencies (Platts, Argus, ICIS) — 1-5 day lag, sampled data, covers mainly exchange-adjacent commodities
- Broker intelligence — anecdotal, biased, inconsistent

This system provides:
- **Daily** implied S&D balance sheets constructed from actual shipment records
- **Continuous** price discovery for commodities with NO published benchmark (raw cashews, sesame, certain rice grades)
- **5-20 day advance warning** on flow anomalies before they reach consensus
- **Counterparty-level** intelligence on who is buying/selling what, from where, at what implied price

### 1.3 Target Users

- Hectar's commodity trading desk (S&D analysts, traders, risk managers)
- Initially internal tool; potential for external licensing to other trading houses

### 1.4 Priority Commodity-Corridor Pairs (Phase 1)

These are the corridors where the system provides maximum edge due to pricing opacity:

| Commodity | Origin(s) | Destination(s) | Why Opaque |
|-----------|-----------|-----------------|------------|
| Raw Cashew Nuts (RCN) | Ivory Coast, Ghana, Nigeria, Tanzania, Mozambique, Guinea-Bissau | India (Tuticorin, Mangalore), Vietnam | No exchange. Prices set by bilateral negotiation. Seasonal. Highly fragmented supply. |
| Sesame Seeds | Sudan, Ethiopia, Nigeria, India, Tanzania | China, Japan, Korea, Turkey | No exchange. Quality-dependent pricing. Conflict-affected origins. |
| Rice (non-basmati) | India, Vietnam, Thailand, Pakistan, Myanmar | West Africa (Nigeria, Ghana, Ivory Coast), East Africa, Middle East | Many grades. Government policy-driven (India export bans). Tender-based. |
| Soybeans (non-CBOT) | Niger, Benin, Nigeria, Mozambique | Regional African, India | Not deliverable against CBOT. Local grades. Informal trade channels. |
| Basmati Rice | India, Pakistan | Middle East (UAE, Saudi), EU | Premium product. Quality/brand fragmentation. |
| Cocoa | Ivory Coast, Ghana, Cameroon, Nigeria | Netherlands, Belgium, USA, Malaysia | Exchange-listed BUT origin differentials are opaque. |
| Shea Nuts/Butter | Ghana, Burkina Faso, Nigeria, Mali | EU, India, USA | Entirely opaque. No published benchmark. |
| Cashew Kernels (processed) | Vietnam, India | USA, EU, Middle East | Processed product. Different grades (W180, W240, W320, etc.). |
| Palm Oil (crude/refined) | Indonesia, Malaysia | India, China, EU, Africa | Exchange-listed BUT origin/grade differentials matter. |
| Cotton | India, West Africa (Mali, Burkina Faso), USA | Bangladesh, Vietnam, China, Turkey | Multiple quality grades. Origin premiums/discounts vary widely. |

---

## 2. PROBLEM STATEMENT

### 2.1 The Pricing Black Hole

For commodities like raw cashew nuts trading between West Africa and Tuticorin, there is NO reliable, continuous price series. What exists:
- Occasional broker quotes (verbal, inconsistent units, unclear incoterms)
- ACA (African Cashew Alliance) seasonal reports — quarterly, backward-looking
- Individual trade deal prices — confidential, non-discoverable

The result: traders operate on intuition, stale data, and information asymmetry. Whoever can construct a continuous implied price curve from actual trade data has a structural advantage.

### 2.2 The S&D Blindspot

For non-exchange commodities, supply-demand balance sheets either don't exist or are updated annually (FAO). Traders have no visibility into:
- Whether West African cashew exports are running above/below seasonal norms
- Whether a new buyer (e.g., a Vietnamese processor) is aggressively accumulating
- Whether origin switching is happening (Tanzania replacing Ivory Coast)
- Whether freight/logistics constraints are tightening specific corridors

### 2.3 The Incoterm Chaos

Customs declarations report values inconsistently:
- Indian import data reports CIF value (cost, insurance, freight included)
- Indian export data reports FOB value
- Some countries report statistical value (which may be CIF or FOB depending on import/export)
- BL (Bill of Lading) data may report face value of invoice (could be any incoterm)
- Currency varies by declaration (USD, EUR, INR, local currency)

Without systematic normalization, raw declared values are **incomparable across countries and corridors**.

---

## 3. DATA SOURCE: EXIMPEDIA TRADE API

### 3.1 API Overview

**Provider**: Eximpedia (https://web.eximpedia.app)
**Authentication**: OAuth2 token-based (tokens expire every 3600 seconds / 1 hour)
**Base URL**: `https://web.eximpedia.app/backend/apis/v1/`
**Rate Limiting**: Credit-points deducted per query; implement caching and rate limiting
**Max Page Size**: 1000 records per request

### 3.2 Authentication Flow

```
POST https://web.eximpedia.app/backend/apis/v1/oauth2/token
Content-Type: application/json

{
  "client_id": "<HECTAR_CLIENT_ID>",
  "client_secret": "<HECTAR_CLIENT_SECRET>"
}

Response:
{
  "AccessToken": "eyJhbGci...",
  "expriesIn": "3600s"
}
```

**Implementation requirement**: Token refresh mechanism that re-authenticates before expiry. Store token in memory, not in persistent storage. Implement a token manager singleton that refreshes at 3000s (5 min before expiry).

### 3.3 Available API Endpoints

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Trade Shipment | `POST /trade/shipment` | Individual shipment records — THE PRIMARY DATA SOURCE |
| Importer Summary | `POST /importer/summary` | Aggregated importer-level data |
| Exporter Summary | `POST /exporter/summary` | Aggregated exporter-level data |

### 3.4 Trade Shipment API — Detailed Specification

This is the **primary endpoint** for the intelligence suite. Each record represents a single shipment line item from a customs declaration.

#### 3.4.1 Request Payload Structure

```json
{
  "DateRange": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  },
  "TradeType": "IMPORT" | "EXPORT",
  "TradeCountry": "<COUNTRY_NAME>",
  "PrimarySearch": {
    "FILTER": "PRODUCT" | "HS_CODE" | "CONSIGNEE" | "CONSIGNOR",
    "VALUES": ["<value1>", "<value2>"],
    "SearchType": "EXACT" | "CONTAIN"
  },
  "AdvanceSearch": [
    {
      "FILTER": "<FILTER_TYPE>",
      "VALUES": ["<value1>"],
      "OPERATOR": "AND" | "OR" | "NOT"
    }
  ],
  "page_size": 1000,
  "page_no": 1,
  "sort": "DATE" | "PRODUCT" | "HS_CODE" | "CONSIGNEE" | "CONSIGNOR",
  "sort_type": "asc" | "desc"
}
```

#### 3.4.2 Available Filters for AdvanceSearch

| FILTER Value | Description | VALUE Format |
|--------------|-------------|--------------|
| `PRODUCT` | Product description text | Strings (max 5) |
| `HS_CODE` | Harmonized System code | Integers: 2, 4, 6, or 8 digits |
| `CONSIGNEE` | Buyer/importer name | Strings (max 5) |
| `CONSIGNOR` | Seller/exporter name | Strings (max 5) |
| `ORIGIN_COUNTRY` | Country of origin/manufacture | Strings (max 5) |
| `DESTINATION_COUNTRY` | Country of destination | Strings (max 5) |
| `ORIGIN_PORT` | Port of loading | Strings (max 5) |
| `DESTINATION_PORT` | Port of discharge | Strings (max 5) |

#### 3.4.3 Operator Logic

The `OPERATOR` field defines how each filter criterion combines with the previous one:
- `AND`: Both conditions must be true
- `OR`: At least one condition must be true
- `NOT`: Excludes records matching this criterion

Query construction example:
```
PRODUCT has_any ("motor parts","tea")
or (HS_CODE between(42000000..42999999) or HS_CODE between(32000000..32999999))
and not(CONSIGNOR has_any ("TESLA","RUSSIA POWER LTD"))
```

#### 3.4.4 Response Data Fields — COMPLETE FIELD REFERENCE

This is the complete set of fields returned by the Trade Shipment API. **Every field listed here must be captured and stored by the ingestion layer.**

**Identifiers:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `RECORD_ID` | String (UUID) | Unique record identifier | Deduplication |
| `RECORDS_TAG` | String (UUID) | Record tag/group identifier | Linking related records |
| `DECLARATION_NO` | String | Customs declaration number | Grouping items within same shipment |
| `BILL_NO` | String | Bill of Lading number | Vessel-level grouping, transshipment detection |
| `INVOICE_NO` | String | Commercial invoice number | Price verification |
| `ITEM_NO` | String | Line item number within declaration | Multi-product shipment parsing |

**Party Information:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `CONSIGNEE` | String | Buyer/importer name | Counterparty graph — demand side |
| `CONSIGNEE_CODE` | String | Buyer identifier code | Entity resolution |
| `CONSIGNEE_ADDRESS` | String | Full buyer address | Entity resolution, geographic clustering |
| `BUYER_NAME` | String | Buyer name (alternate field) | Entity resolution |
| `BUYER_ADDRESS` | String | Buyer address (alternate field) | Entity resolution |
| `CONSIGNOR` | String | Seller/exporter name | Counterparty graph — supply side |
| `EXPORTER_NAME` | String | Exporter name (alternate field for export data) | Entity resolution |
| `ADDRESS` | String | Exporter address | Entity resolution |
| `DECLARANT_CODE` | String | Customs declarant code | Logistics company identification |
| `DECLARANT_NAME` | String | Logistics company/CHA/freight forwarder | Supply chain mapping |
| `CHA_NAME` | String | Customs House Agent name | Supply chain mapping |
| `IEC` | String | Importer-Exporter Code (India-specific) | Entity resolution for Indian entities |

**Location Details:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `ORIGIN_PORT` | String | Port of loading/shipment | Route identification, freight estimation |
| `DESTINATION_PORT` | String | Port of discharge/receipt | Route identification, freight estimation |
| `FOREIGN_PORT` | String | Foreign port (India-specific: opposite port) | Route identification |
| `INDIAN_PORT` | String | Indian port (India-specific) | Route identification |
| `ORIGIN_COUNTRY` | String | Country of origin/manufacture | Origin analysis, S&D attribution |
| `DESTINATION_COUNTRY` | String | Country of destination | Demand analysis, S&D attribution |
| `COUNTRY` | String | Trade partner country | Redundant with origin/destination |
| `COUNTRY_ISO_CODE_2` | String | ISO 2-letter country code | Standardization |
| `CITY` | String | City of declarant | Geographic granularity |
| `STATE` | String | State/province | Geographic granularity |
| `PIN` | String | Postal code | Geographic granularity |

**Product Information:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `HS_CODE` | String | Full HS code (up to 8 digits) | **PRIMARY** product classification |
| `HS_CODE_2` | String | 2-digit HS chapter | Commodity group classification |
| `HS_CODE_4` | String | 4-digit HS heading | Sub-commodity classification |
| `HS_CODE_DESCRIPTION` | String | Official HS code description | Product standardization |
| `PRODUCT` | String (free-text) | Actual product description from invoice | **CRITICAL** — contains grade, quality, specification details not in HS code |
| `PRODUCT_DESCRIPTION` | String (free-text) | Extended product description | Grade/quality inference |

**Quantity and Measurements:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `QUANTITY` | Float | Declared quantity | Volume analysis |
| `UNIT` | String | Unit of measurement (KGS, NOS, MTS, etc.) | **MUST NORMALIZE** — see Section 6.3 |
| `STD_QUANTITY` | Float | Standardized quantity | Pre-normalized quantity |
| `STD_UNIT` | String | Standardized unit | Pre-normalized unit |

**Financial Information:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `FOB_INR` | Float | FOB value in Indian Rupees | **PRIMARY PRICE DATA** (for Indian export data) |
| `FOB_USD` | Float | FOB value in US Dollars | **PRIMARY PRICE DATA** (for Indian export data) |
| `UNIT_PRICE_LC` | Float | Unit price in local currency | Price per unit calculation |
| `UNIT_PRICE_USD` | Float | Unit price in US Dollars | **PRIMARY PRICE DATA** (universal) |
| `TOTAL_VALUE_LC` | Float | Total value in local currency | Cross-check |
| `TOTAL_VALUE_USD` | Float | Total value in US Dollars | Cross-check |
| `TOTAL_AMOUNT_INV_FC` | Float | Total amount in invoice foreign currency | Original invoice value |
| `ITEM_RATE_INR` | Float | Item rate in INR | Per-item pricing |
| `ITEM_RATE_INV` | Float | Item rate in invoice currency | Per-item pricing (original currency) |
| `STD_ITEM_RATE_INR` | Float | Standardized item rate in INR | Normalized per-item pricing |
| `STD_ITEM_RATE_INV` | Float | Standardized item rate in invoice currency | Normalized per-item pricing |
| `CURRENCY` | String | Invoice currency (INR, USD, EUR, etc.) | FX normalization |
| `USD_EXCHANGE_RATE` | Float | USD exchange rate used | FX normalization |
| `TOTAL_DUTY_PAID` | Float | Duty paid | Landed cost calculation |
| `DRAWBACK` | Float | Duty drawback amount | Net cost calculation |
| `CUSH` | String | Custom house code | Regulatory identification |

**Temporal Information:**
| Field | Type | Description | Intelligence Use |
|-------|------|-------------|-----------------|
| `DATE` | ISO DateTime | Date of shipment/declaration | **PRIMARY** time series key |
| `EXP_DATE` | ISO DateTime | Export date (for export records) | Time series key |

### 3.5 Importer Summary API

**Endpoint**: `POST https://web.eximpedia.app/backend/apis/v1/importer/summary`

Returns aggregated data per importer, including:
- `IMPORTER_NAME`: Entity name
- `TOTAL_VALUE_USD`: Aggregate trade value
- `Total_Quantity`: Aggregate quantity
- `HSCode_Product_Description`: Array of HS code + description pairs
- `HS_Codes`: Array of HS codes traded
- `Origin_Ports`: Array of origin ports used
- `Destination_Ports`: Array of destination ports used
- `Origin_Countries`: Array of origin countries

**Use case**: Counterparty profiling, market share analysis, sourcing pattern detection.

Additional parameter: `exclude` field (value: "CONSIGNOR") to hide counterparty names from summary view.

### 3.6 Exporter Summary API

**Endpoint**: `POST https://web.eximpedia.app/backend/apis/v1/exporter/summary`

Mirrors Importer Summary but for the export side:
- `SUPPLIER_NAME`: Entity name
- `TOTAL_VALUE_USD`: Aggregate trade value
- `Total_Quantity`: Aggregate quantity
- Same port, country, and HS code arrays

Additional parameter: `exclude` field (value: "CONSIGNEE") to hide buyer names.

### 3.7 Country Coverage

The system has access to customs data from the following countries, organized by data type:

#### Custom Countries (Direct Customs Data — Most Detailed)

**IMPORT data available:**
Argentina, Bangladesh, BL Brazil, Brazil, Bolivia, Botswana, Burundi, Cameroon, Chile, Colombia, Costa Rica, Ecuador, Ethiopia, Ghana, India, Indonesia (2 datasets), Ivory Coast, Kazakhstan, Kenya, Lesotho, Liberia, Mexico, Moldova, Namibia, Nicaragua, Nigeria, Pakistan, Panama, Paraguay, Peru, Philippines, Rwanda, South Sudan, Sri Lanka, Tanzania, Turkey, Uganda, Ukraine, Uruguay, USA, Uzbekistan, Venezuela, Vietnam (2 datasets), Zimbabwe, Russia, Angola, Malawi, Sao Tome, Malaysia, Armenia

**EXPORT data available:**
Argentina, Bangladesh, BL Brazil, Botswana, Cameroon, Chile, Colombia, Costa Rica, Ecuador, Ethiopia, Ghana, India, Indonesia (2 datasets), Ivory Coast, Kazakhstan, Lesotho, Mexico, Moldova, Namibia, Nicaragua, Nigeria, Pakistan, Panama, Paraguay, Peru, Philippines, Rwanda, Sri Lanka, Tanzania, Turkey, Uganda, Ukraine, Uruguay, Uzbekistan, Venezuela, Vietnam (2 datasets), Zimbabwe, Russia, Angola, Malawi, Sao Tome, Malaysia, Armenia

**Data freshness**: Most countries updated to July-September 2025. Some lag (Moldova: May 2023, Venezuela: July/Aug 2024).

#### BL Countries (Bill of Lading Data — Less Granular on Price)

Import + Export coverage for: Algeria, Australia, Bahrain, Bangladesh, Belgium, Canada, China, Denmark, Djibouti, Egypt, Finland, France, Germany, Ghana, Greece, India, Indonesia, Iran, Iraq, Italy, Japan, Korea, Kuwait, Malaysia, Mexico, Netherlands, Norway, Oman, Pakistan, Philippines, Qatar, Saudi Arabia, Singapore, Spain, Sri Lanka, Taiwan, Thailand, UAE, United Kingdom, USA, Vietnam

**BL data period**: Mostly Jan 2020 - Dec 2022 (HISTORICAL ONLY for most). Pakistan updated to Sep 2025.

#### Silk Route Data
- Import: Jan 2020 - Nov 2024
- Export: Jan 2020 - Nov 2024

**CRITICAL NOTE FOR IMPLEMENTATION**: BL country data is largely historical (ended Dec 2022) while Custom Countries data is current. The system must prioritize Custom Countries data for live intelligence and use BL data for historical pattern training and backtesting only.

---

## 4. SYSTEM ARCHITECTURE

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DECISION LAYER (L4)                       │
│  Spot Heatmap │ Arb Scanner │ Alerts │ S&D Dashboard        │
├─────────────────────────────────────────────────────────────┤
│                  INTELLIGENCE LAYER (L3)                     │
│  Flow Anomaly │ Implied S&D │ Counterparty Graph │ Predictor│
├─────────────────────────────────────────────────────────────┤
│                NORMALIZATION ENGINE (L2)                      │
│  Incoterm Decomp │ HS Mapper │ Unit Harmonizer │ Grade Inf. │
├─────────────────────────────────────────────────────────────┤
│                  DATA INGESTION LAYER (L1)                   │
│  Eximpedia API │ Freight Feeds │ FX Feeds │ Ground Prices   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow

```
Eximpedia API ──→ Raw Record Store ──→ Normalization Pipeline ──→ Normalized Record Store
                                                                         │
Ground Prices ──→ Price Observation Store ──────────────────────────────→│
                                                                         ▼
Freight Feeds ──→ Freight Rate Store ──→ ┌─────────────────────────────────┐
FX Feeds ──────→ FX Rate Store ────────→ │    Intelligence Computation     │
                                          │    Engine (Batch + Streaming)   │
                                          └──────────────┬──────────────────┘
                                                         ▼
                                          ┌─────────────────────────────────┐
                                          │   Derived Intelligence Store    │
                                          │   (S&D, Signals, Predictions)   │
                                          └──────────────┬──────────────────┘
                                                         ▼
                                          ┌─────────────────────────────────┐
                                          │     Trader-Facing Dashboard     │
                                          └─────────────────────────────────┘
```

---

## 5. MODULE 1: DATA INGESTION LAYER

### 5.1 Eximpedia Data Harvester

#### 5.1.1 Harvesting Strategy

The system must systematically pull data from Eximpedia for all priority commodity-corridor combinations. Given the API's credit-point billing model and 1000-record page limit, the harvester must be intelligent about what it queries.

**Harvesting configuration** — define as a YAML/JSON config:

```yaml
harvest_jobs:
  - name: "cashew_india_import"
    trade_type: "IMPORT"
    trade_country: "INDIA"
    primary_search:
      filter: "HS_CODE"
      values: [0801]  # 4-digit: cashew nuts
      search_type: "CONTAIN"
    advance_search:
      - filter: "ORIGIN_COUNTRY"
        values: ["IVORY COAST", "GHANA", "NIGERIA", "TANZANIA", "MOZAMBIQUE"]
        operator: "AND"
    schedule: "daily"
    lookback_days: 30
    
  - name: "cashew_vietnam_import"
    trade_type: "IMPORT"
    trade_country: "VIETNAM"
    primary_search:
      filter: "HS_CODE"
      values: [0801]
      search_type: "CONTAIN"
    schedule: "daily"
    lookback_days: 30

  - name: "sesame_global_export"
    trade_type: "EXPORT"
    trade_country: "ETHIOPIA"
    primary_search:
      filter: "HS_CODE"
      values: [1207]  # 4-digit: oil seeds
      search_type: "CONTAIN"
    schedule: "daily"
    lookback_days: 30

  - name: "rice_india_export"
    trade_type: "EXPORT"
    trade_country: "INDIA"
    primary_search:
      filter: "HS_CODE"
      values: [1006]  # 4-digit: rice
      search_type: "CONTAIN"
    schedule: "daily"
    lookback_days: 30

  # ... additional jobs defined per priority corridor
```

#### 5.1.2 HS Code Reference for Priority Commodities

| Commodity | HS Chapter (2-digit) | HS Heading (4-digit) | Key 6/8-digit Codes | Notes |
|-----------|---------------------|---------------------|---------------------|-------|
| Cashew Nuts (raw, in shell) | 08 | 0801 | 08013100, 08013200 | 31=in shell, 32=shelled |
| Sesame Seeds | 12 | 1207 | 12074000 | 40=sesame |
| Rice (non-basmati) | 10 | 1006 | 10063010-90 | Varies by milling degree |
| Rice (basmati) | 10 | 1006 | 10063020 | India-specific subcode |
| Soybeans | 12 | 1201 | 12019000 | 90=other soybeans |
| Cocoa Beans | 18 | 1801 | 18010000 | Raw cocoa beans |
| Shea Nuts | 12 | 1207 | 12079990 | Often classified under "other oil seeds" |
| Cashew Kernels | 08 | 0801 | 08013200 | Shelled/processed |
| Palm Oil (crude) | 15 | 1511 | 15111000 | 10=crude |
| Palm Oil (refined) | 15 | 1511 | 15119000 | 90=other/refined |
| Cotton | 52 | 5201 | 52010000 | Raw cotton, not carded |

**IMPORTANT**: HS codes vary by country at the 6-8 digit level. The system must build an HS code harmonization layer (see Section 6.2) that maps country-specific subcodes to a unified commodity taxonomy.

#### 5.1.3 Pagination and Full Data Pull

```python
# Pseudocode for complete data extraction
async def harvest_job(config):
    token = await get_valid_token()
    page = 1
    total_fetched = 0
    
    while True:
        payload = build_payload(config, page_no=page, page_size=1000)
        response = await api_call(
            url="https://web.eximpedia.app/backend/apis/v1/trade/shipment",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            body=payload
        )
        
        records = response["data"]
        total_records = response["total_records"]
        
        await store_raw_records(records, config.name)
        total_fetched += len(records)
        
        if total_fetched >= total_records or len(records) == 0:
            break
        
        page += 1
        await rate_limit_pause()  # Respect API rate limits
    
    return total_fetched
```

#### 5.1.4 Deduplication

Records may appear across overlapping date range queries. Deduplicate on:
- Primary key: `RECORD_ID`
- Secondary check: `DECLARATION_NO` + `ITEM_NO` + `DATE`
- Tertiary check (for BL data): `BILL_NO` + `HS_CODE` + `QUANTITY` + `TOTAL_VALUE_USD`

#### 5.1.5 Data Freshness Monitoring

Implement an alert system that tracks:
- Last successful harvest per job
- Data latency (most recent record date vs. today)
- Record count anomalies (sudden drops/spikes vs. historical norms)
- Country-specific outages (Eximpedia may lag on certain countries)

### 5.2 Supplementary Data Feeds

These feeds are NOT from Eximpedia. They must be sourced separately and integrated.

#### 5.2.1 Freight Rate Feeds

| Feed | Coverage | Use |
|------|----------|-----|
| Baltic Exchange (BDI, BSI, BCI, BHSI) | Dry bulk routes | Bulk commodity freight normalization |
| Freightos Baltic Index (FBX) | Container routes | Container commodity freight |
| Platts Bunker Prices | Global bunker ports | Fuel cost component of freight |
| Clarksons / Drewry | Historical voyage rates | Route-specific freight curves |

**Minimum viable implementation**: Build a manual freight rate table initially, updated weekly, for key routes:

```json
{
  "route_id": "ABIDJAN-TUTICORIN-HANDYSIZE",
  "origin_port": "ABIDJAN",
  "destination_port": "TUTICORIN",
  "vessel_class": "HANDYSIZE",
  "rate_per_mt": 42.50,
  "currency": "USD",
  "effective_date": "2026-02-01",
  "source": "broker_quote",
  "notes": "RCN season rate, 25-30k DWT"
}
```

#### 5.2.2 FX Rate Feeds

**Source**: European Central Bank (ECB) daily rates or FRED (Federal Reserve Economic Data)
- Capture: USD, EUR, GBP, INR, CNY, JPY, VND, BRL, KES, TZS, GHS, NGN, XOF (CFA Franc), PKR, BDT, LKR, IDR, MYR, THB
- Historical rates going back to earliest data point
- Store as: `fx_rate(currency, date) → rate_vs_USD`

**CRITICAL**: For Indian customs data, the `USD_EXCHANGE_RATE` field is provided in the API response. Use this for Indian data normalization as it represents the rate used at declaration time. For other countries, use ECB daily rates.

#### 5.2.3 Insurance Rate Reference

Build a simple lookup table:

```json
{
  "commodity_group": "agricultural_dry_bulk",
  "route_risk": "standard",
  "insurance_rate_pct": 0.15,  // % of cargo value
  "war_risk_surcharge_pct": 0.00,
  "notes": "Standard marine cargo insurance"
}
```

Override for high-risk routes (Red Sea, Gulf of Guinea):
```json
{
  "commodity_group": "agricultural_dry_bulk",
  "route_risk": "gulf_of_guinea",
  "insurance_rate_pct": 0.15,
  "war_risk_surcharge_pct": 0.25,
  "notes": "Piracy surcharge applicable"
}
```

#### 5.2.4 Port Charge Reference

Maintain a table of estimated port handling charges per port:

```json
{
  "port": "TUTICORIN",
  "country": "INDIA",
  "handling_charge_per_mt": 3.50,
  "wharfage_per_mt": 1.20,
  "total_port_charge_per_mt": 4.70,
  "currency": "USD",
  "last_updated": "2026-01-01"
}
```

---

## 6. MODULE 2: NORMALIZATION ENGINE

This is the first and most critical competitive moat. Every raw record must pass through this pipeline before it becomes useful intelligence.

### 6.1 Incoterm Normalization

#### 6.1.1 The Core Problem

Different countries and trade types declare values on different incoterm bases:

| TradeCountry | TradeType | Declared Value Basis | Available Price Fields |
|-------------|-----------|---------------------|----------------------|
| INDIA | EXPORT | **FOB** | `FOB_INR`, `FOB_USD`, `ITEM_RATE_INR` |
| INDIA | IMPORT | **CIF** (assessable value) | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD`, `ITEM_RATE_INR` |
| BANGLADESH | IMPORT | **CIF** | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| VIETNAM | IMPORT | **CIF** | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| ETHIOPIA | EXPORT | **FOB** | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| NIGERIA | IMPORT | **CIF** | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| USA | IMPORT | **CIF** (customs value) | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| INDONESIA | IMPORT | **CIF** | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| BRAZIL | EXPORT | **FOB** | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |
| BL data (all) | Both | **Varies** (often CIF or commercial invoice) | `UNIT_PRICE_USD`, `TOTAL_VALUE_USD` |

#### 6.1.2 Normalization Target

**Normalize ALL records to FOB origin basis in USD.**

FOB (Free on Board) origin is chosen because:
- It represents the price at the point of export, independent of logistics
- It allows direct comparison of the same commodity across different origins
- Freight can be added back to convert to CIF destination when needed
- It's the standard basis for commodity benchmarking

#### 6.1.3 Normalization Algorithms

**Algorithm A: CIF → FOB Conversion (for import data)**

```
Price_FOB_USD = Price_CIF_USD - Freight(origin_port, dest_port, vessel_class, date)
                               - Insurance(commodity_group, route_risk, cargo_value)
                               - Port_Charges_Destination(dest_port)

Where:
  Freight = lookup(freight_rate_table, origin_port, dest_port, nearest_date)
  Insurance = Price_CIF_USD × insurance_rate_pct(commodity_group, route_risk)
  Port_Charges = lookup(port_charge_table, dest_port)
```

**Algorithm B: FOB origin (already FOB, just currency normalization)**

```
Price_FOB_USD = FOB_USD  (if available directly)
              OR
              = FOB_INR / USD_EXCHANGE_RATE  (for Indian export data)
              OR
              = TOTAL_VALUE_LC / fx_rate(currency, date)  (for other countries)
```

**Algorithm C: Handling BL data (unknown incoterm basis)**

For BL data where incoterm is uncertain:
1. If the record has both `ORIGIN_PORT` and `DESTINATION_PORT`, assume CIF destination and apply Algorithm A
2. If only origin port is available, assume FOB and apply Algorithm B
3. Flag record with `incoterm_confidence: "LOW"` for BL-derived normalizations
4. Cross-validate against nearby Custom Countries data for the same corridor

**Algorithm D: Unit Price Calculation**

```
unit_price_fob_usd = Price_FOB_USD / quantity_in_standard_units

Where:
  quantity_in_standard_units = normalize_quantity(QUANTITY, UNIT, commodity)
```

#### 6.1.4 Handling Edge Cases

**Edge Case 1: Missing or zero prices**
- If `UNIT_PRICE_USD` is 0 or null but `TOTAL_VALUE_USD` and `QUANTITY` exist:
  `implied_unit_price = TOTAL_VALUE_USD / QUANTITY`
- If all price fields are null: flag record as `price_status: "MISSING"`, exclude from price analytics but include in volume analytics

**Edge Case 2: Extreme outliers**
- Calculate rolling median price for commodity×corridor×month
- If a record's unit price is >3σ from the rolling median, flag as `price_status: "OUTLIER"`
- Do NOT delete outliers — they may represent genuine market moves. Store flag and let the intelligence layer decide.

**Edge Case 3: Multi-currency invoices**
- Some records show `CURRENCY: "EUR"` but `TOTAL_VALUE_USD` is also populated
- Prefer USD fields when available
- If only LC (local currency) values exist, convert using `fx_rate(CURRENCY, DATE)`
- If `USD_EXCHANGE_RATE` is provided (Indian data), use it — it's the official rate at declaration

**Edge Case 4: Transshipment de-duplication**
- The same cargo may appear twice: once as export from origin country, once as import to destination country
- ALSO may appear as import+export through a transshipment hub (Singapore, UAE, Netherlands)
- De-duplication strategy:
  1. Match on: `HS_CODE` (4-digit) + `QUANTITY` (±5%) + `DATE` (±30 days) + compatible port pairs
  2. If match found, link records as `transshipment_group`
  3. Use the ORIGIN COUNTRY's export record for FOB price (most accurate)
  4. Use the DESTINATION COUNTRY's import record for CIF price (most accurate for landed cost)

**Edge Case 5: Systematic under/over-declaration**
- Some origins systematically under-declare customs value (to reduce duty)
- Detect by comparing: for the same commodity, same period, origin A's declared prices vs. origin B's
- Build a `declaration_bias_factor` per country×commodity, calibrated against PRA prices where available
- Apply as: `adjusted_price = declared_price × declaration_bias_factor`
- Initially set all factors to 1.0; refine over time with ground truth data

### 6.2 HS Code Harmonization

#### 6.2.1 The Problem

HS codes are globally harmonized at the 6-digit level but diverge at 8+ digits per country's national tariff schedule. The same product may have different 8-digit codes in India vs. Vietnam vs. Nigeria.

#### 6.2.2 Solution: Hectar Commodity Taxonomy (HCT)

Build a hierarchical commodity taxonomy that maps HS codes to Hectar's internal classification:

```json
{
  "hct_id": "HCT-0801-RCN-INSHELL",
  "hct_name": "Raw Cashew Nuts (In Shell)",
  "hct_group": "Cashew Complex",
  "hct_supergroup": "Tree Nuts",
  "hs_mappings": [
    {"country": "*", "hs_code": "080131", "confidence": "HIGH"},
    {"country": "INDIA", "hs_code": "08013110", "confidence": "HIGH"},
    {"country": "INDIA", "hs_code": "08013120", "confidence": "HIGH"},
    {"country": "VIETNAM", "hs_code": "08013100", "confidence": "HIGH"},
    {"country": "IVORY COAST", "hs_code": "080131", "confidence": "HIGH"}
  ],
  "standard_unit": "MT",
  "quality_grades": ["Grade A (180+ nuts/kg)", "Grade B (180-210)", "Grade C (210+)"],
  "grade_inference_rules": [
    {"condition": "origin_country IN ('IVORY COAST', 'GHANA') AND month IN (3,4,5)", "inferred_grade": "Grade A (main crop)"},
    {"condition": "origin_country IN ('TANZANIA', 'MOZAMBIQUE') AND month IN (10,11,12)", "inferred_grade": "Grade B (bimodal crop)"}
  ]
}
```

#### 6.2.3 Product Description Mining

The `PRODUCT` and `PRODUCT_DESCRIPTION` free-text fields often contain critical quality/grade information that HS codes cannot capture. Examples:

- `"RAW CASHEW NUTS IN SHELL ORIGIN IVORY COAST OUTTURN 47 LBS"` → grade indicator: outturn 47 lbs = high quality
- `"HULLED SESAME SEEDS 99.95% PURITY AFLATOXIN FREE"` → premium quality
- `"INDIAN LONG GRAIN WHITE RICE 5% BROKEN"` → specific grade (5% broken)
- `"PREMIUM BASMATI RICE 1121 SELLA"` → variety (1121) and processing (sella/parboiled)

**Implementation**: Build a commodity-specific regex/NLP parser that extracts:
- Quality indicators (purity %, outturn, broken %, moisture %)
- Variety/cultivar names (1121, Sugandha, NERICA, etc.)
- Processing state (raw, hulled, parboiled, polished, bleached)
- Grade classifications (W180, W240, W320 for cashew kernels)
- Origin claims (sometimes embedded in description)

```python
# Example parser for cashew product descriptions
def parse_cashew_description(text):
    result = {
        "state": None,       # raw_in_shell, shelled, kernel
        "outturn": None,     # KOR (kernel outturn ratio) in lbs
        "nut_count": None,   # nuts per kg
        "origin_claim": None,
        "grade": None
    }
    
    text_upper = text.upper()
    
    # State detection
    if "IN SHELL" in text_upper or "RCN" in text_upper:
        result["state"] = "raw_in_shell"
    elif "KERNEL" in text_upper or any(g in text_upper for g in ["W180", "W240", "W320", "W450"]):
        result["state"] = "kernel"
    elif "SHELLED" in text_upper:
        result["state"] = "shelled"
    
    # Outturn extraction
    outturn_match = re.search(r'OUTTURN\s*(\d+\.?\d*)\s*LBS', text_upper)
    if outturn_match:
        result["outturn"] = float(outturn_match.group(1))
    
    # Kernel grade
    grade_match = re.search(r'(W\d{3}|WW\d{3}|SW\d{3}|LWP|SWP|BB|SS)', text_upper)
    if grade_match:
        result["grade"] = grade_match.group(1)
    
    return result
```

### 6.3 Unit Harmonization

#### 6.3.1 The Problem

The `UNIT` field contains heterogeneous values: KGS, MTS, NOS, LTR, PCS, BAGS, CBM, SQM, DOZ, SET, etc.

#### 6.3.2 Standard Unit per Commodity

| HCT Supergroup | Standard Unit | Standard Unit Symbol |
|----------------|---------------|---------------------|
| Grains & Cereals | Metric Tonnes | MT |
| Oilseeds | Metric Tonnes | MT |
| Tree Nuts | Metric Tonnes | MT |
| Vegetable Oils | Metric Tonnes | MT |
| Cotton | Metric Tonnes | MT |
| Cocoa | Metric Tonnes | MT |
| Sugar | Metric Tonnes | MT |

#### 6.3.3 Conversion Table

```json
{
  "KGS": {"to_MT": 0.001},
  "MTS": {"to_MT": 1.0},
  "NOS": {"to_MT": null, "note": "Requires commodity-specific weight per piece"},
  "BAGS": {"to_MT": null, "note": "Requires bag weight. Standard cashew bag = 80kg"},
  "LBS": {"to_MT": 0.000453592},
  "QUINTAL": {"to_MT": 0.1},
  "TON": {"to_MT": 1.0},
  "LONG TON": {"to_MT": 1.01605},
  "SHORT TON": {"to_MT": 0.907185},
  "CBM": {"to_MT": null, "note": "Volume; requires density conversion"},
  "LTR": {"to_MT": null, "note": "Volume; requires density. Palm oil ≈ 0.92 kg/L"},
  "GAL": {"to_MT": null, "note": "Volume; 1 US gallon = 3.785 L"}
}
```

**Commodity-specific conversions:**
```json
{
  "cashew_nut_bags": {"bag_weight_kg": 80, "to_MT": 0.08},
  "rice_bags_india": {"bag_weight_kg": 50, "to_MT": 0.05},
  "rice_bags_thailand": {"bag_weight_kg": 50, "to_MT": 0.05},
  "cocoa_bags": {"bag_weight_kg": 60, "to_MT": 0.06},
  "cotton_bales_india": {"bale_weight_kg": 170, "to_MT": 0.17},
  "palm_oil_litre": {"density_kg_per_l": 0.92, "to_MT": 0.00092}
}
```

If `UNIT` is `NOS` and the commodity is a bulk agricultural product, this is likely a data quality issue. Attempt to resolve using `STD_QUANTITY` and `STD_UNIT` fields if available. If not, flag record as `unit_status: "UNRESOLVABLE"` and exclude from volume analytics.

### 6.4 Quality/Grade Inference Engine

For opaque commodities, the system must infer quality/grade from available signals since there is no explicit grade field in customs data.

#### 6.4.1 Inference Signals

| Signal | Weight | Example |
|--------|--------|---------|
| Product description parsing | HIGH | "W240" in description → Cashew kernel grade W240 |
| Unit price relative to corridor median | MEDIUM | Price >20% above median → likely premium grade |
| Origin + Season | MEDIUM | Ivory Coast cashews in March → main crop (higher quality) |
| Consignee profile | LOW | Known premium buyer → likely premium grade |
| Origin port | LOW | Specific ports associated with specific grades |

#### 6.4.2 Grade Assignment Output

Each normalized record gets a `quality_estimate` field:

```json
{
  "quality_estimate": {
    "grade": "Premium",
    "confidence": 0.72,
    "signals_used": ["product_description_match", "price_position", "origin_season"],
    "grade_detail": "RCN outturn ~47 lbs, main crop Ivory Coast"
  }
}
```

---

## 7. MODULE 3: INTELLIGENCE LAYER

This is where raw data becomes trading intelligence.

### 7.1 Implied Price Curve (IPC)

#### 7.1.1 Definition

For each commodity × origin × incoterm basis, compute a daily "implied market price" from the cloud of individual shipment prices.

```
IPC(commodity, origin, date) = WeightedMedian(
    prices = [normalized_fob_usd_per_mt for all records 
              WHERE hct_commodity = commodity 
              AND origin_country = origin
              AND date BETWEEN (date - 5 trading days) AND date],
    weights = [quantity_mt for each record]
)
```

**Why weighted median instead of mean:**
- Median is robust to outliers (mis-declarations, special deals)
- Volume-weighting ensures large commercial shipments count more than small parcels
- 5-day rolling window smooths daily noise while remaining responsive

#### 7.1.2 Confidence Scoring

```
IPC_confidence(commodity, origin, date) = function_of(
    n_records: count of records in window,
    volume_coverage: total MT in window vs. historical average,
    price_dispersion: IQR of prices in window,
    data_recency: days since most recent record
)

Scoring:
  - n_records >= 20 AND volume_coverage >= 0.8 AND IQR/median < 0.15 → HIGH
  - n_records >= 5 AND volume_coverage >= 0.3 → MEDIUM
  - else → LOW
```

#### 7.1.3 IPC for Opaque Commodities — Special Treatment

For commodities like raw cashew nuts (West Africa → India), the system may only have 2-10 shipment records per day. The standard IPC calculation needs adaptation:

- Extend rolling window to 10-15 trading days
- Lower confidence threshold (n_records >= 3 for MEDIUM)
- Cross-validate with Vietnamese import prices for the same origin (if available)
- Apply seasonal adjustment based on historical price patterns
- Flag when IPC is based on <5 records: `"ipc_note": "thin market — directional signal only"`

### 7.2 Flow Velocity Index (FVI)

#### 7.2.1 Definition

Measures acceleration or deceleration of trade volumes for a given commodity × corridor.

```
FVI(commodity, route, date) = 
    Sum(quantity_mt WHERE date BETWEEN (date-7) AND date) /
    Sum(quantity_mt WHERE date BETWEEN (date-37) AND (date-30))
```

#### 7.2.2 Interpretation

| FVI Value | Signal | Trading Implication |
|-----------|--------|---------------------|
| > 1.30 | Strong acceleration | Demand surge OR supply rush to ship before deadline (e.g., export ban) |
| 1.10 - 1.30 | Moderate acceleration | Sustained demand increase |
| 0.90 - 1.10 | Normal | Business as usual |
| 0.70 - 0.90 | Moderate deceleration | Demand pullback OR supply shortage |
| < 0.70 | Severe deceleration | Crop failure, policy intervention, logistics disruption |

#### 7.2.3 Seasonality Adjustment

Agricultural commodities have strong seasonal patterns. A raw FVI of 0.6 during an inter-crop period is normal, not a signal.

```
FVI_adjusted(commodity, route, date) = 
    FVI_raw(commodity, route, date) / 
    FVI_seasonal_norm(commodity, route, day_of_year)

Where:
    FVI_seasonal_norm = average FVI for this commodity/route/day_of_year 
                        over the past 3 years
```

### 7.3 Implied Supply-Demand Balance Sheet

#### 7.3.1 Construction

For each priority commodity, maintain a running S&D balance sheet:

```
SUPPLY SIDE:
  Beginning_Stocks = Previous_period_ending_stocks (external source or estimated)
  + Production = External estimate (FAO, USDA, national statistics)
  + Imports = Sum(quantity_mt, import records, this period)  ← FROM EXIMPEDIA

DEMAND SIDE:
  Domestic_Consumption = Production + Imports - Exports (implied)
  + Exports = Sum(quantity_mt, export records, this period)  ← FROM EXIMPEDIA
  + Ending_Stocks = Supply - Demand (implied)

FLOW-BASED UPDATE (daily):
  Today's implied_net_trade_flow = exports_today - imports_today
  Running_cumulative_vs_seasonal_norm = sum(daily_net_flow) - expected_cumulative
```

#### 7.3.2 The Killer Signal: Deviation from Expected

The most valuable output is NOT the absolute S&D — it's the **deviation** from consensus:

```
S&D_delta(commodity, country, date) = 
    Hectar_implied_cumulative_exports(year_to_date) - 
    USDA_or_consensus_export_estimate_prorated_to_date

If S&D_delta is significantly negative:
  → Country is UNDER-SHIPPING vs. expectations
  → Supply likely tighter than market thinks
  → Bullish signal for the commodity

If S&D_delta is significantly positive:
  → Country is OVER-SHIPPING vs. expectations
  → Supply more ample than market thinks
  → Bearish signal
```

**Example**: India's rice export ban analysis
- USDA projects India rice exports at X million MT for the year
- By June, Hectar's implied cumulative exports from Indian customs data = Y million MT
- If Y << prorated X → ban is tighter than expected → bullish for Thai/Viet rice
- If Y >> prorated X → ban is leaking → bearish for alternatives

### 7.4 Counterparty Intelligence Graph

#### 7.4.1 Entity Resolution

The same company appears under many names across records:
- "OLAM INTERNATIONAL" / "OLAM AGRI" / "OLAM FOOD INGREDIENTS" / "OLAM NIGERIA LTD"
- "LOUIS DREYFUS" / "LDC" / "LOUIS DREYFUS COMPANY B.V."

Build an entity resolution system:
1. Exact match on `CONSIGNEE_CODE` / `IEC` where available
2. Fuzzy string matching on entity names (Levenshtein distance, Jaro-Winkler)
3. Address-based clustering (same address = same entity group)
4. Manual override table for known entity aliases

```json
{
  "hectar_entity_id": "HE-001-OLAM",
  "canonical_name": "Olam Group",
  "entity_type": "major_trader",
  "aliases": [
    "OLAM INTERNATIONAL",
    "OLAM AGRI",
    "OLAM FOOD INGREDIENTS",
    "OLAM NIGERIA LIMITED",
    "OLAM GHANA LIMITED",
    "OLAM VIETNAM"
  ],
  "known_commodities": ["cashew", "cocoa", "coffee", "rice", "cotton", "sesame"],
  "entity_class": "ABCD_major"  // One of: ABCD_major, regional_trader, processor, end_user, government
}
```

#### 7.4.2 Graph Construction

Build a directed graph:
- **Nodes**: Entities (exporters, importers), Ports, Countries
- **Edges**: Trade flows (weighted by volume and value)
- **Temporal layers**: Monthly snapshots for trend analysis

#### 7.4.3 Counterparty Signals

| Signal | Detection Method | Trading Implication |
|--------|-----------------|---------------------|
| New buyer enters corridor | Entity not seen in this commodity × corridor in past 12 months | New demand source; potential price support |
| Major buyer withdrawal | Known regular buyer's volume drops >50% | Demand destruction or sourcing shift |
| Origin switching | Buyer maintains volume but shifts origin mix | Supply stress at original origin |
| Concentration increase | HHI of suppliers to a destination rises | Supply vulnerability; potential premium |
| Stockpile signal | Single entity receives >2x normal volume in compressed timeframe | Strategic accumulation; bullish |

### 7.5 Freight-Adjusted Basis (FAB) Calculator

```
FAB(commodity, origin, destination, date) = 
    IPC_FOB(commodity, origin, date)
    + Live_Freight(origin_port, dest_port, date)
    + Insurance(commodity, route)
    + Port_Charges(origin_port + dest_port)
    - Published_CIF_Benchmark(commodity, destination, date)  [if available]
```

For opaque commodities with NO published benchmark, the FAB becomes the benchmark itself — Hectar's reconstructed CIF price IS the price discovery.

### 7.6 Corridor Substitution Score (CSS)

Measures whether a destination is diversifying or concentrating its supply sources.

```
CSS(commodity, destination, date) = 
    HHI(origin_shares, current_quarter) / HHI(origin_shares, same_quarter_last_year)

Where:
    HHI = Sum(market_share_i²) for each origin country i
    market_share_i = volume_from_origin_i / total_import_volume
```

Rising CSS (>1.0) = fewer origins dominating = supply stress
Falling CSS (<1.0) = diversification = supply comfort

### 7.7 Ensemble Spot Rate Predictor

#### 7.7.1 Feature Vector

For each commodity × corridor × day, construct:

```python
features = {
    # Flow signals
    "fvi_7d": flow_velocity_index_7day,
    "fvi_30d": flow_velocity_index_30day,
    "fvi_adj": seasonality_adjusted_fvi,
    
    # Price signals
    "ipc_change_5d": pct_change(ipc, 5),
    "ipc_change_15d": pct_change(ipc, 15),
    "ipc_vs_90d_avg": ipc_today / ipc_90d_avg,
    "price_dispersion": iqr_of_recent_prices / median_of_recent_prices,
    
    # Basis signals  
    "fab_current": freight_adjusted_basis,
    "fab_change_5d": change_in_fab_over_5_days,
    
    # Structure signals
    "css_current": corridor_substitution_score,
    "css_change": css_quarterly_change,
    "hhi_buyers": buyer_concentration_index,
    
    # Macro signals
    "freight_momentum": pct_change(freight_rate, 15),
    "fx_momentum": pct_change(relevant_fx_pair, 15),
    
    # Seasonal
    "day_of_year": date.timetuple().tm_yday,
    "crop_year_progress": pct_of_crop_year_elapsed,
    
    # Volume
    "volume_vs_norm": recent_volume / historical_seasonal_norm,
    "sd_delta": implied_export_vs_consensus_prorated,
}
```

#### 7.7.2 Model Architecture

Start with an interpretable ensemble:

```
Stage 1: Linear model (Ridge regression) for directional signal
    ΔPrice(t+n) ~ α·FVI + β·ΔIPC + γ·FAB + δ·CSS + ε·Freight + ζ·FX + Seasonal

Stage 2: Gradient-boosted classifier for confidence scoring
    P(Price_UP | features) → [0, 1]
    
Stage 3: Combine
    Signal = {
        "direction": "UP" | "DOWN" | "FLAT",
        "magnitude_estimate": from Stage 1,
        "confidence": from Stage 2,
        "horizon": n days (1, 5, 15)
    }
```

**CRITICAL: For opaque commodities, the model should start in "observation mode" only — collecting data and computing features without making predictions until at least 6 months of normalized data has been accumulated. Premature predictions on thin data will erode trust.**

---

## 8. MODULE 4: DECISION LAYER (TRADER UI)

### 8.1 Design Philosophy

**Super minimalistic. Ruthlessly intuitive.** Traders don't have time for dashboards. They need:
1. What changed since last session? (Alerts)
2. What's the implied price for commodity X on corridor Y? (IPC lookup)
3. Is the S&D tighter or looser than I think? (S&D delta)
4. Who's buying and who's selling? (Counterparty view)

### 8.2 Core Views

#### 8.2.1 Home: Signal Feed

A chronological feed of the most important signals, ordered by impact score:

```
[🔴 HIGH] Ivory Coast RCN exports to India down 35% vs. seasonal norm (FVI: 0.65)
    → Implied FOB Abidjan: $1,285/MT (+3.2% vs. last week)
    → Only 3 origins active to Tuticorin (CSS: 1.45, rising)
    5 hours ago

[🟡 MEDIUM] New buyer detected: Vietnamese processor entering Sudan sesame corridor
    → Entity: "LONG SON JOINT STOCK CO" — 3 shipments in 10 days, 450 MT total
    → Historical: This entity previously sourced only from Ethiopia
    2 hours ago

[🟢 LOW] Indian rice (non-basmati, 5% broken) exports running 12% above seasonal
    → Cumulative YTD: 14.2M MT vs. 12.7M MT same period last year
    → Key destination shift: West Africa +22%, Middle East -8%
    1 day ago
```

#### 8.2.2 Commodity Deep Dive

For any commodity, show:
- IPC chart (time series) with confidence bands
- Volume chart (daily shipments, 7-day MA)
- Origin breakdown (pie chart, evolving over time)
- Top buyers and sellers (table with volume, value, trend)
- S&D delta chart (Hectar implied vs. consensus)

#### 8.2.3 Corridor Explorer

Select: Origin × Destination × Commodity
Show:
- Implied FOB at origin
- + Freight estimate
- + Insurance
- + Port charges
- = Implied CIF at destination
- vs. Published benchmark (if exists)
- = Basis (premium/discount)

#### 8.2.4 Counterparty Profile

For any entity, show:
- Total volume and value by commodity
- Origin/destination distribution
- Historical activity chart
- Unusual activity flags
- Related entities (same group)

#### 8.2.5 Arbitrage Scanner

Real-time comparison of:
- Same commodity, different origins → FOB comparison
- Same origin, different destinations → demand competition
- Spot vs. flow-implied forward price → temporal arbitrage

### 8.3 Alert Configuration

Traders can configure alerts on:
- IPC crosses threshold (absolute price or % change)
- FVI breaches threshold (acceleration/deceleration)
- New counterparty enters monitored corridor
- S&D delta exceeds ±X%
- Freight rate spike on monitored route
- Country data goes stale (no new records for N days)

---

## 9. PRIORITY COMMODITY CORRIDORS — DETAILED SPECIFICATIONS

### 9.1 Raw Cashew Nuts (RCN): West Africa → India/Vietnam

**Why this is the #1 priority**: Largest opaque commodity corridor by value. $3-4B annual trade. No published benchmark. Seasonal. Highly fragmented supply. India and Vietnam compete fiercely for supply.

#### 9.1.1 Data Collection Plan

| Query | TradeType | TradeCountry | HS Code | Advance Filters |
|-------|-----------|-------------|---------|-----------------|
| India RCN imports | IMPORT | INDIA | 0801 | ORIGIN_COUNTRY IN (IVORY COAST, GHANA, NIGERIA, TANZANIA, MOZAMBIQUE, GUINEA BISSAU, BENIN) |
| Vietnam RCN imports | IMPORT | VIETNAM | 0801 | — |
| Ivory Coast RCN exports | EXPORT | IVORY COAST | 0801 | — |
| Ghana RCN exports | EXPORT | GHANA | 0801 | — |
| Nigeria RCN exports | EXPORT | NIGERIA | 0801 | — |
| Tanzania RCN exports | EXPORT | TANZANIA | 0801 | — |
| India cashew kernel exports | EXPORT | INDIA | 0801 | (to track processed output) |

**Note**: For countries not in Eximpedia's direct coverage, use BL data (historical) + mirror data from partner countries.

#### 9.1.2 Seasonal Calendar

```
WEST AFRICA (main crop): February - June (Ivory Coast, Ghana, Guinea-Bissau)
EAST AFRICA: October - January (Tanzania, Mozambique)
INDIA (domestic): February - May (minor; India is primarily a processor, not grower)
VIETNAM: No domestic production; 100% imported for processing

Peak shipping: March - July (West Africa → India/Vietnam)
Processing season: Year-round in India/Vietnam (inventory-dependent)
Kernel export peak: August - December (processed output)
```

#### 9.1.3 Key Intelligence Questions to Answer

1. What is the current implied FOB price for RCN at Abidjan/Tema/Lagos?
2. How does this compare to the same week last year?
3. Is India or Vietnam buying more aggressively? (FVI comparison)
4. Are there signs of crop shortfall? (Total exports vs. seasonal norm)
5. Which specific processors in India are accumulating? (Counterparty)
6. What's the implied conversion spread? (RCN import price vs. kernel export price)

### 9.2 Sesame Seeds: Africa → Asia

#### 9.2.1 Key Corridors

| Origin | Destination | Season | Notes |
|--------|-------------|--------|-------|
| Sudan | China, Japan, Turkey | Oct-Feb | Conflict risk, quality variability |
| Ethiopia | China, Japan, Israel | Nov-Mar | Premium hulled quality |
| Nigeria | China, Japan | Apr-Sep | Multiple crops per year |
| India | Multiple | Feb-May (rabi), Oct-Nov (kharif) | Both importer and exporter |
| Tanzania | China, Japan | Jun-Sep | Growing origin |

#### 9.2.2 Data Collection

| Query | TradeType | TradeCountry | HS Code |
|-------|-----------|-------------|---------|
| India sesame exports | EXPORT | INDIA | 1207 |
| India sesame imports | IMPORT | INDIA | 1207 |
| Ethiopia sesame exports | EXPORT | ETHIOPIA | 1207 |
| Nigeria sesame exports | EXPORT | NIGERIA | 1207 |
| Tanzania sesame exports | EXPORT | TANZANIA | 1207 |

**Sudan challenge**: Sudan is NOT in Eximpedia's country list. Sesame from Sudan must be tracked via:
- Import records of destination countries (China, Japan, Turkey)
- BL data (if available under Silk Route)
- Origin country filters on import queries of destination countries

### 9.3 Rice (Non-Basmati): India/Vietnam/Thailand → Africa/Middle East

#### 9.3.1 Grade Classification from Product Description

| Grade Keyword | Grade Name | Typical Price Tier |
|---------------|------------|-------------------|
| "5% BROKEN" or "5PCT" | Parboiled 5% broken | Premium |
| "25% BROKEN" | Parboiled 25% broken | Mid |
| "100% BROKEN" | Brokens | Value |
| "LONG GRAIN WHITE" | White rice | Premium-mid |
| "PARBOILED" | Parboiled | Mid |
| "1121 SELLA" or "PUSA 1121" | Basmati 1121 parboiled | Super premium |
| "BASMATI" | Basmati | Premium |
| "PONNI" or "SONA MASURI" | South Indian varieties | Specialty |

#### 9.3.2 India Rice Policy Monitoring

India's rice export policy has been volatile (bans, MEPs, restrictions). The system must track:
- Implied export volumes vs. pre-policy levels
- Shift in destination mix (policy may exempt some destinations)
- Substitute origin gains (Vietnam, Thailand, Myanmar)

---

## 10. ALGORITHM SPECIFICATIONS

### 10.1 Complete Normalization Pipeline — Code Specification

```python
class NormalizationPipeline:
    """
    Processes a single raw trade record and outputs a normalized record.
    Must be called for every record ingested from Eximpedia.
    """
    
    def normalize(self, raw_record: dict, trade_type: str, trade_country: str) -> dict:
        """
        Args:
            raw_record: Single record from Eximpedia API response
            trade_type: "IMPORT" or "EXPORT"
            trade_country: Country whose customs data this is from
        
        Returns:
            Normalized record with standardized fields
        """
        normalized = {}
        
        # Step 1: Determine incoterm basis of declared value
        incoterm_basis = self.infer_declared_incoterm(trade_type, trade_country)
        
        # Step 2: Extract best available price
        price_usd, price_source = self.extract_price_usd(raw_record, trade_country)
        
        # Step 3: Extract and standardize quantity
        quantity_mt, unit_status = self.standardize_quantity(
            raw_record, 
            self.classify_commodity(raw_record)
        )
        
        # Step 4: Normalize to FOB USD
        if incoterm_basis == "FOB":
            fob_usd = price_usd
            fob_source = "direct_fob"
        elif incoterm_basis == "CIF":
            freight = self.lookup_freight(
                raw_record.get("ORIGIN_PORT"),
                raw_record.get("DESTINATION_PORT"),
                raw_record.get("DATE")
            )
            insurance = self.calc_insurance(price_usd, raw_record)
            port_charges = self.lookup_port_charges(
                raw_record.get("DESTINATION_PORT")
            )
            fob_usd = price_usd - freight - insurance - port_charges
            fob_source = "derived_from_cif"
        else:
            fob_usd = price_usd  # Best guess
            fob_source = "assumed_unknown_basis"
        
        # Step 5: Calculate unit price
        if quantity_mt and quantity_mt > 0:
            unit_price_fob_usd_per_mt = fob_usd / quantity_mt
        else:
            unit_price_fob_usd_per_mt = None
        
        # Step 6: Outlier detection
        price_status = self.check_outlier(
            unit_price_fob_usd_per_mt,
            self.classify_commodity(raw_record),
            raw_record.get("ORIGIN_COUNTRY"),
            raw_record.get("DATE")
        )
        
        # Step 7: Quality/grade inference
        quality_estimate = self.infer_quality(raw_record)
        
        # Step 8: Commodity classification
        hct = self.classify_commodity(raw_record)
        
        # Assemble normalized record
        normalized = {
            # Identifiers (pass through)
            "record_id": raw_record.get("RECORD_ID"),
            "declaration_no": raw_record.get("DECLARATION_NO"),
            "bill_no": raw_record.get("BILL_NO"),
            
            # Standardized fields
            "date": raw_record.get("DATE") or raw_record.get("EXP_DATE"),
            "trade_type": trade_type,
            "trade_country": trade_country,
            
            # Parties (pass through, entity resolution applied separately)
            "consignee": raw_record.get("CONSIGNEE") or raw_record.get("BUYER_NAME"),
            "consignor": raw_record.get("CONSIGNOR") or raw_record.get("EXPORTER_NAME"),
            
            # Location
            "origin_country": raw_record.get("ORIGIN_COUNTRY"),
            "origin_port": raw_record.get("ORIGIN_PORT"),
            "destination_country": raw_record.get("DESTINATION_COUNTRY"),
            "destination_port": raw_record.get("DESTINATION_PORT"),
            
            # Commodity
            "hs_code": raw_record.get("HS_CODE"),
            "hs_code_2": raw_record.get("HS_CODE_2"),
            "hs_code_4": raw_record.get("HS_CODE_4"),
            "product_description": raw_record.get("PRODUCT") or raw_record.get("PRODUCT_DESCRIPTION"),
            "hct_id": hct["hct_id"],
            "hct_name": hct["hct_name"],
            "hct_group": hct["hct_group"],
            
            # Quantity (normalized)
            "quantity_mt": quantity_mt,
            "quantity_original": raw_record.get("QUANTITY"),
            "unit_original": raw_record.get("UNIT"),
            "unit_status": unit_status,
            
            # Price (normalized)
            "fob_usd_total": fob_usd,
            "fob_usd_per_mt": unit_price_fob_usd_per_mt,
            "declared_incoterm": incoterm_basis,
            "price_source": fob_source,
            "price_status": price_status,
            "currency_original": raw_record.get("CURRENCY"),
            
            # Enrichments
            "quality_estimate": quality_estimate,
            "freight_used": freight if incoterm_basis == "CIF" else None,
            "insurance_used": insurance if incoterm_basis == "CIF" else None,
            
            # Metadata
            "normalized_at": datetime.utcnow().isoformat(),
            "normalization_version": "1.0"
        }
        
        return normalized
    
    def infer_declared_incoterm(self, trade_type: str, trade_country: str) -> str:
        """
        Determines the incoterm basis of the declared value based on
        country customs reporting conventions.
        """
        INCOTERM_MAP = {
            ("EXPORT", "INDIA"): "FOB",
            ("IMPORT", "INDIA"): "CIF",
            ("EXPORT", "BRAZIL"): "FOB",
            ("IMPORT", "BANGLADESH"): "CIF",
            ("IMPORT", "VIETNAM"): "CIF",
            ("EXPORT", "VIETNAM"): "FOB",
            ("IMPORT", "NIGERIA"): "CIF",
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
            ("EXPORT", "NIGERIA"): "FOB",
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
        }
        
        return INCOTERM_MAP.get(
            (trade_type, trade_country), 
            "FOB" if trade_type == "EXPORT" else "CIF"  # Default assumption
        )
```

### 10.2 Seasonal Decomposition Specification

Each commodity has a crop year and seasonal pattern. The system must encode these:

```json
{
  "HCT-0801-RCN-INSHELL": {
    "crop_years": [
      {
        "name": "West African Main Crop",
        "start_month": 2,
        "end_month": 7,
        "peak_months": [3, 4, 5],
        "origins": ["IVORY COAST", "GHANA", "GUINEA BISSAU", "BENIN"]
      },
      {
        "name": "East African Crop",
        "start_month": 10,
        "end_month": 1,
        "peak_months": [11, 12],
        "origins": ["TANZANIA", "MOZAMBIQUE"]
      }
    ],
    "seasonal_volume_weights": {
      "1": 0.06, "2": 0.08, "3": 0.14, "4": 0.16, "5": 0.14,
      "6": 0.10, "7": 0.07, "8": 0.05, "9": 0.04, "10": 0.05,
      "11": 0.06, "12": 0.05
    }
  },
  "HCT-1207-SESAME": {
    "crop_years": [
      {
        "name": "Sudan/Ethiopia Main",
        "start_month": 10,
        "end_month": 3,
        "peak_months": [11, 12, 1],
        "origins": ["SUDAN", "ETHIOPIA"]
      },
      {
        "name": "Nigeria Multi-crop",
        "start_month": 4,
        "end_month": 9,
        "peak_months": [6, 7, 8],
        "origins": ["NIGERIA"]
      },
      {
        "name": "India Rabi",
        "start_month": 2,
        "end_month": 5,
        "peak_months": [3, 4],
        "origins": ["INDIA"]
      }
    ]
  },
  "HCT-1006-RICE-NONBASMATI": {
    "crop_years": [
      {
        "name": "India Kharif",
        "start_month": 10,
        "end_month": 9,
        "peak_export_months": [1, 2, 3, 4],
        "origins": ["INDIA"]
      },
      {
        "name": "Vietnam Winter-Spring",
        "start_month": 2,
        "end_month": 5,
        "peak_export_months": [3, 4, 5],
        "origins": ["VIETNAM"]
      },
      {
        "name": "Thailand Main",
        "start_month": 11,
        "end_month": 4,
        "peak_export_months": [1, 2, 3],
        "origins": ["THAILAND"]
      }
    ]
  }
}
```

---

## 11. GROUND PRICE COLLECTION INTEGRATION

### 11.1 Purpose

Customs data-derived prices have a structural lag (time between deal and customs declaration can be 2-8 weeks). Ground-collected prices — from brokers, market agents, local offices — provide real-time calibration.

### 11.2 Data Model for Ground Prices

```json
{
  "observation_id": "GP-20260223-001",
  "commodity": "HCT-0801-RCN-INSHELL",
  "price": 1320.00,
  "currency": "USD",
  "unit": "MT",
  "incoterm": "FOB",
  "location": "ABIDJAN",
  "quality_grade": "Outturn 47-48 lbs",
  "source_type": "broker_quote",  // broker_quote | field_agent | auction | tender_result
  "source_name": "Jean-Claude (Abidjan broker)",
  "observation_date": "2026-02-23",
  "confidence": "MEDIUM",
  "notes": "Spot price for immediate shipment. Seller asking $1,350.",
  "entered_by": "hectar_analyst_01",
  "verified": false
}
```

### 11.3 Integration with IPC

Ground prices serve as **calibration anchors** for the customs-derived IPC:

```
Calibrated_IPC(commodity, origin, date) = 
    α × IPC_customs_derived(date) + 
    (1-α) × IPC_ground_prices(date)

Where:
    α = function of relative data freshness and volume
    
    If customs data is <7 days old and has >10 records: α = 0.7
    If customs data is 7-30 days old: α = 0.5
    If customs data is >30 days old: α = 0.2
    If no customs data: α = 0.0 (rely entirely on ground prices)
```

### 11.4 Ground Price Collection UI

Mobile-friendly form for field agents/analysts:
- Commodity (dropdown from HCT)
- Price + Currency + Unit
- Incoterm (FOB/CIF/CFR/CPT/other)
- Location (port/market)
- Quality grade (commodity-specific dropdown)
- Source type
- Free-text notes
- Photo upload (for auction boards, contract documents)

### 11.5 Price Validation Rules

Automatically flag ground prices that are:
- >20% different from latest IPC (possible error or genuine market move)
- Duplicate of an existing observation (same commodity, price, location, date)
- From a source with historically low accuracy
- In a currency inconsistent with the location

---

## 12. DATA MODEL & SCHEMA

### 12.1 Core Tables

```sql
-- Raw records from Eximpedia (immutable)
CREATE TABLE raw_trade_records (
    record_id VARCHAR PRIMARY KEY,
    ingestion_timestamp TIMESTAMP,
    harvest_job_name VARCHAR,
    trade_type VARCHAR(6),       -- IMPORT or EXPORT
    trade_country VARCHAR(50),
    raw_payload JSONB             -- Complete API response record
);

-- Normalized records (derived from raw)
CREATE TABLE normalized_records (
    record_id VARCHAR PRIMARY KEY REFERENCES raw_trade_records,
    normalized_at TIMESTAMP,
    normalization_version VARCHAR(10),
    
    -- Temporal
    trade_date DATE,
    
    -- Parties
    consignee VARCHAR(500),
    consignor VARCHAR(500),
    consignee_entity_id VARCHAR(50),  -- Resolved entity
    consignor_entity_id VARCHAR(50),  -- Resolved entity
    
    -- Location
    origin_country VARCHAR(50),
    origin_port VARCHAR(100),
    destination_country VARCHAR(50),
    destination_port VARCHAR(100),
    
    -- Commodity
    hs_code VARCHAR(10),
    hs_code_2 VARCHAR(2),
    hs_code_4 VARCHAR(4),
    hct_id VARCHAR(50),
    product_description TEXT,
    quality_estimate JSONB,
    
    -- Quantity
    quantity_mt DECIMAL(15,4),
    unit_status VARCHAR(20),
    
    -- Price
    fob_usd_total DECIMAL(15,2),
    fob_usd_per_mt DECIMAL(12,4),
    declared_incoterm VARCHAR(10),
    price_source VARCHAR(50),
    price_status VARCHAR(20),      -- NORMAL, OUTLIER, MISSING
    
    -- Normalization metadata
    freight_deducted DECIMAL(10,2),
    insurance_deducted DECIMAL(10,2),
    port_charges_deducted DECIMAL(10,2)
);

-- Implied Price Curve
CREATE TABLE ipc_daily (
    ipc_date DATE,
    hct_id VARCHAR(50),
    origin_country VARCHAR(50),
    incoterm VARCHAR(10),
    
    price_usd_per_mt DECIMAL(12,4),
    confidence VARCHAR(10),          -- HIGH, MEDIUM, LOW
    n_records INTEGER,
    volume_mt DECIMAL(15,4),
    price_iqr DECIMAL(12,4),
    
    PRIMARY KEY (ipc_date, hct_id, origin_country, incoterm)
);

-- Flow Velocity Index
CREATE TABLE fvi_daily (
    fvi_date DATE,
    hct_id VARCHAR(50),
    origin_country VARCHAR(50),
    destination_country VARCHAR(50),
    
    fvi_raw DECIMAL(8,4),
    fvi_seasonally_adjusted DECIMAL(8,4),
    volume_7d_mt DECIMAL(15,4),
    volume_30d_mt DECIMAL(15,4),
    
    PRIMARY KEY (fvi_date, hct_id, origin_country, destination_country)
);

-- Supply-Demand Tracker
CREATE TABLE sd_tracker (
    sd_date DATE,
    hct_id VARCHAR(50),
    country VARCHAR(50),
    
    cumulative_exports_mt DECIMAL(15,4),
    cumulative_imports_mt DECIMAL(15,4),
    consensus_export_estimate_mt DECIMAL(15,4),
    consensus_import_estimate_mt DECIMAL(15,4),
    sd_delta_exports DECIMAL(15,4),
    sd_delta_imports DECIMAL(15,4),
    
    PRIMARY KEY (sd_date, hct_id, country)
);

-- Ground Price Observations
CREATE TABLE ground_prices (
    observation_id VARCHAR PRIMARY KEY,
    hct_id VARCHAR(50),
    price DECIMAL(12,4),
    currency VARCHAR(3),
    unit VARCHAR(10),
    incoterm VARCHAR(10),
    location VARCHAR(100),
    quality_grade VARCHAR(100),
    source_type VARCHAR(30),
    source_name VARCHAR(200),
    observation_date DATE,
    confidence VARCHAR(10),
    notes TEXT,
    entered_by VARCHAR(50),
    verified BOOLEAN DEFAULT FALSE
);

-- Entity Resolution Table
CREATE TABLE entities (
    entity_id VARCHAR PRIMARY KEY,
    canonical_name VARCHAR(500),
    entity_type VARCHAR(30),
    entity_class VARCHAR(30),
    aliases TEXT[],
    known_commodities TEXT[],
    metadata JSONB
);

-- Freight Rate Reference
CREATE TABLE freight_rates (
    route_id VARCHAR,
    origin_port VARCHAR(100),
    destination_port VARCHAR(100),
    vessel_class VARCHAR(50),
    rate_per_mt DECIMAL(10,2),
    currency VARCHAR(3),
    effective_date DATE,
    source VARCHAR(100),
    PRIMARY KEY (route_id, effective_date)
);

-- Alerts/Signals
CREATE TABLE signals (
    signal_id VARCHAR PRIMARY KEY,
    signal_date TIMESTAMP,
    signal_type VARCHAR(50),
    severity VARCHAR(10),          -- HIGH, MEDIUM, LOW
    hct_id VARCHAR(50),
    corridor VARCHAR(200),
    headline TEXT,
    detail JSONB,
    time_advantage_days INTEGER,
    acknowledged BOOLEAN DEFAULT FALSE
);
```

---

## 13. API INTEGRATION PATTERNS

### 13.1 Token Management

```python
import asyncio
import time
import httpx

class EximpediaTokenManager:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = 0
        self._lock = asyncio.Lock()
    
    async def get_token(self) -> str:
        async with self._lock:
            if self.token and time.time() < (self.token_expiry - 300):
                return self.token
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://web.eximpedia.app/backend/apis/v1/oauth2/token",
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                data = response.json()
                self.token = data["AccessToken"]
                self.token_expiry = time.time() + 3600
                return self.token
```

### 13.2 Rate-Limited API Client

```python
class EximpediaClient:
    BASE_URL = "https://web.eximpedia.app/backend/apis/v1"
    
    def __init__(self, token_manager: EximpediaTokenManager):
        self.token_manager = token_manager
        self.semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests
    
    async def trade_shipment(self, payload: dict) -> dict:
        return await self._request("/trade/shipment", payload)
    
    async def importer_summary(self, payload: dict) -> dict:
        return await self._request("/importer/summary", payload)
    
    async def exporter_summary(self, payload: dict) -> dict:
        return await self._request("/exporter/summary", payload)
    
    async def _request(self, endpoint: str, payload: dict) -> dict:
        async with self.semaphore:
            # Rate limiting
            now = time.time()
            wait = self.min_request_interval - (now - self.last_request_time)
            if wait > 0:
                await asyncio.sleep(wait)
            
            token = await self.token_manager.get_token()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}{endpoint}",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    },
                    json=payload
                )
                self.last_request_time = time.time()
                
                if response.status_code != 200:
                    raise EximpediaAPIError(
                        f"API returned {response.status_code}: {response.text}"
                    )
                
                return response.json()
```

### 13.3 Query Builder

```python
class QueryBuilder:
    """Builds valid Eximpedia API payloads from high-level parameters."""
    
    @staticmethod
    def build_shipment_query(
        start_date: str,
        end_date: str,
        trade_type: str,
        trade_country: str,
        hs_codes: list[int] = None,
        products: list[str] = None,
        origin_countries: list[str] = None,
        destination_countries: list[str] = None,
        origin_ports: list[str] = None,
        destination_ports: list[str] = None,
        consignees: list[str] = None,
        consignors: list[str] = None,
        page_size: int = 1000,
        page_no: int = 1,
        sort: str = "DATE",
        sort_type: str = "desc"
    ) -> dict:
        
        payload = {
            "DateRange": {
                "start_date": start_date,
                "end_date": end_date
            },
            "TradeType": trade_type,
            "TradeCountry": trade_country,
            "page_size": min(page_size, 1000),
            "page_no": page_no,
            "sort": sort,
            "sort_type": sort_type
        }
        
        # Primary search (required)
        if hs_codes:
            payload["PrimarySearch"] = {
                "FILTER": "HS_CODE",
                "VALUES": hs_codes[:5],  # Max 5 values
                "SearchType": "CONTAIN"
            }
        elif products:
            payload["PrimarySearch"] = {
                "FILTER": "PRODUCT",
                "VALUES": products[:5],
                "SearchType": "CONTAIN"
            }
        
        # Advance search (optional filters)
        advance_search = []
        
        if origin_countries:
            advance_search.append({
                "FILTER": "ORIGIN_COUNTRY",
                "VALUES": origin_countries[:5],
                "OPERATOR": "AND"
            })
        
        if destination_countries:
            advance_search.append({
                "FILTER": "DESTINATION_COUNTRY",
                "VALUES": destination_countries[:5],
                "OPERATOR": "AND"
            })
        
        if origin_ports:
            advance_search.append({
                "FILTER": "ORIGIN_PORT",
                "VALUES": origin_ports[:5],
                "OPERATOR": "AND"
            })
        
        if destination_ports:
            advance_search.append({
                "FILTER": "DESTINATION_PORT",
                "VALUES": destination_ports[:5],
                "OPERATOR": "AND"
            })
        
        if consignees:
            advance_search.append({
                "FILTER": "CONSIGNEE",
                "VALUES": consignees[:5],
                "OPERATOR": "AND"
            })
        
        if consignors:
            advance_search.append({
                "FILTER": "CONSIGNOR",
                "VALUES": consignors[:5],
                "OPERATOR": "AND"
            })
        
        if advance_search:
            payload["AdvanceSearch"] = advance_search
        
        return payload
```

---

## 14. DEPLOYMENT & INFRASTRUCTURE

### 14.1 Recommended Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Data Ingestion | Python (asyncio + httpx) | Async API calls, flexible parsing |
| Data Store | PostgreSQL + TimescaleDB | Time-series optimized, JSONB support |
| Computation Engine | Python (pandas, numpy, scikit-learn) | Rapid prototyping, rich ecosystem |
| Task Scheduler | Celery + Redis | Reliable job scheduling for harvests |
| API Layer | FastAPI | Async, auto-docs, Pydantic validation |
| Frontend | React + Tailwind | Minimalist, component-based |
| Cache | Redis | IPC caching, session management |
| Monitoring | Prometheus + Grafana | System health, data freshness |

### 14.2 Scaling Considerations

- **API credits**: Monitor Eximpedia credit consumption. Implement query optimization to minimize redundant pulls (incremental date-based harvesting).
- **Storage**: Estimate ~500 bytes per normalized record. At 100K records/day across all commodities and corridors = ~50MB/day = ~18GB/year. Modest.
- **Computation**: IPC, FVI, CSS computations are lightweight. Ensemble model training is weekly/monthly. No GPU needed initially.

---

## 15. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-8)

**Goal**: Data pipeline operational. Normalized records flowing for top 3 commodities.

| Week | Deliverable |
|------|------------|
| 1-2 | Eximpedia API integration (auth, client, pagination, rate limiting) |
| 3-4 | Raw data harvester with job configs for RCN, sesame, rice |
| 5-6 | Normalization engine (incoterm, HS mapper, unit harmonizer) |
| 7-8 | Basic IPC computation, data quality dashboard |

**Exit criteria**: Daily normalized data feed for RCN (West Africa → India), sesame (Ethiopia/Nigeria → global), rice (India → global). Basic IPC with confidence scores.

### Phase 2: Intelligence (Weeks 9-16)

**Goal**: Actionable intelligence features. S&D tracking. Alert system.

| Week | Deliverable |
|------|------------|
| 9-10 | FVI computation, seasonality adjustment, S&D delta tracker |
| 11-12 | Entity resolution engine, counterparty graph construction |
| 13-14 | FAB calculator, corridor comparison tool |
| 15-16 | Alert system, basic trader dashboard (read-only) |

**Exit criteria**: Traders can see daily implied prices, flow signals, and counterparty activity for priority commodities. Alerts on major anomalies.

### Phase 3: Prediction & Scale (Weeks 17-24)

**Goal**: Predictive signals. Full commodity coverage. Ground price integration.

| Week | Deliverable |
|------|------------|
| 17-18 | Ensemble predictor (observation mode), ground price collection app |
| 19-20 | Arb scanner, additional commodity corridors (cocoa, cotton, palm) |
| 21-22 | Backtesting framework, model calibration |
| 23-24 | Full production deployment, monitoring, user training |

**Exit criteria**: Predictive signals for top 5 commodities with backtested accuracy metrics. Ground price integration live. Full trader workflow supported.

### Phase 4: Optimization & Expansion (Ongoing)

- Add remaining Eximpedia countries/commodities
- Integrate live freight feeds (Baltic Exchange API)
- Build ML-based entity resolution
- NLP-powered product description parsing
- Mobile app for ground price collection
- External client access (licensing revenue)

---

## 16. APPENDICES

### Appendix A: Eximpedia API Quick Reference Card

| Action | Endpoint | Method |
|--------|----------|--------|
| Get auth token | `/oauth2/token` | POST |
| Trade shipments | `/trade/shipment` | POST |
| Importer summary | `/importer/summary` | POST |
| Exporter summary | `/exporter/summary` | POST |

**Max page_size**: 1000
**Token lifetime**: 3600 seconds
**Max filter values**: 5 per filter
**Available filter types**: PRODUCT, HS_CODE, CONSIGNEE, CONSIGNOR, ORIGIN_COUNTRY, DESTINATION_COUNTRY, ORIGIN_PORT, DESTINATION_PORT
**Available operators**: AND, OR, NOT
**Search types (PrimarySearch only)**: EXACT, CONTAIN

### Appendix B: Country Availability Matrix for Priority Commodities

| Commodity | Origin Available? | Destination Available? | Data Gaps |
|-----------|------------------|----------------------|-----------|
| RCN (West Africa → India) | IVORY COAST ✅, GHANA ✅, NIGERIA ✅, TANZANIA ✅ | INDIA ✅, VIETNAM ✅ | Guinea-Bissau ❌, Mozambique ❌ (use BL/mirror data) |
| Sesame (Africa → Asia) | ETHIOPIA ✅, NIGERIA ✅, TANZANIA ✅ | INDIA ✅ | Sudan ❌ (critical gap — use destination import mirror), China ❌ (use BL only, stale) |
| Rice (India → Africa) | INDIA ✅ | NIGERIA ✅, GHANA ✅, IVORY COAST ✅ | Many African destinations not covered — use India export data as primary |
| Soybeans (Africa) | NIGERIA ✅ | INDIA ✅ | Niger ❌, Benin ❌ |
| Cocoa | IVORY COAST ✅, GHANA ✅, CAMEROON ✅, NIGERIA ✅ | — | Destination (Netherlands, Belgium) only in BL (stale) |

### Appendix C: Key Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Eximpedia API downtime | Data gaps | Implement retry logic, store last-known state, alert on staleness |
| Credit point exhaustion | Cannot query | Monitor credits, optimize queries, negotiate credit increase |
| Customs data lag (2-8 weeks from shipment to declaration) | Signals are lagging | Ground price integration, cross-validate with partner country data, use export data (often faster than import data) |
| Systematic under-declaration | Price signals biased | Build bias correction factors, calibrate against ground truth |
| Entity name inconsistency | Counterparty analysis broken | Invest in robust entity resolution, maintain manual override table |
| Freight rate estimation error | FOB normalization inaccurate | Start with conservative estimates, refine with ground truth, quantify error margins |
| Thin data for opaque commodities | Low IPC confidence | Wider rolling windows, lower thresholds, explicit confidence labeling, supplement with ground prices |
| Country coverage gaps | Cannot track some corridors | Use mirror data (track via partner country's import/export data), BL data (historical), Silk Route data |

### Appendix D: Glossary

| Term | Definition |
|------|-----------|
| **BL** | Bill of Lading — transport document issued by carrier |
| **CIF** | Cost, Insurance, and Freight — seller delivers goods on board vessel, pays freight and insurance to destination |
| **CSS** | Corridor Substitution Score — measures supply concentration changes |
| **FAB** | Freight-Adjusted Basis — difference between reconstructed and published prices |
| **FOB** | Free on Board — seller delivers goods on board vessel at origin port |
| **FVI** | Flow Velocity Index — measures volume acceleration/deceleration |
| **HCT** | Hectar Commodity Taxonomy — internal commodity classification system |
| **HHI** | Herfindahl-Hirschman Index — concentration measure (sum of squared market shares) |
| **HS Code** | Harmonized System Code — international product classification (WCO) |
| **IPC** | Implied Price Curve — volume-weighted median price derived from customs data |
| **PRA** | Price Reporting Agency (Platts, Argus, ICIS, etc.) |
| **RCN** | Raw Cashew Nut (in shell) |
| **S&D** | Supply and Demand |
| **WASDE** | World Agricultural Supply and Demand Estimates (USDA report) |

---

*This document is the single source of truth for building the Hectar Commodity Flow Intelligence Suite. Every module, algorithm, data field, and integration pattern specified here has been designed with the actual Eximpedia API capabilities and limitations in mind. Builders should follow this specification exactly and flag any API behavior that deviates from what is documented here.*

*Last updated: 2026-02-23*
*Classification: CONFIDENTIAL — HECTAR INTERNAL*
