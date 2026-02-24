"""Build valid Eximpedia API payloads from high-level parameters."""

from datetime import date, timedelta


class QueryBuilder:
    """Constructs well-formed Eximpedia API query payloads.

    Ensures:
    - Filter value limits (max 5 per filter) are respected
    - Page size capped at 1000
    - Date ranges properly formatted
    - Advance search filters combined with correct operators
    """

    @staticmethod
    def build_shipment_query(
        start_date: str | date,
        end_date: str | date,
        trade_type: str,
        trade_country: str,
        hs_codes: list[int] | None = None,
        products: list[str] | None = None,
        origin_countries: list[str] | None = None,
        destination_countries: list[str] | None = None,
        origin_ports: list[str] | None = None,
        destination_ports: list[str] | None = None,
        consignees: list[str] | None = None,
        consignors: list[str] | None = None,
        page_size: int = 1000,
        page_no: int = 1,
        sort: str = "DATE",
        sort_type: str = "desc",
    ) -> dict:
        if isinstance(start_date, date):
            start_date = start_date.isoformat()
        if isinstance(end_date, date):
            end_date = end_date.isoformat()

        payload: dict = {
            "DateRange": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "TradeType": trade_type.upper(),
            "TradeCountry": trade_country.upper(),
            "page_size": min(page_size, 1000),
            "page_no": page_no,
            "sort": sort,
            "sort_type": sort_type,
        }

        # Primary search — required
        # Eximpedia API requires HS code values as strings with leading zeros
        if hs_codes:
            payload["PrimarySearch"] = {
                "FILTER": "HS_CODE",
                "VALUES": [str(c).zfill(4) if c < 1000 else str(c) for c in hs_codes][:5],
                "SearchType": "CONTAIN",
            }
        elif products:
            payload["PrimarySearch"] = {
                "FILTER": "PRODUCT",
                "VALUES": products[:5],
                "SearchType": "CONTAIN",
            }

        # Advance search filters
        advance_search: list[dict] = []

        filter_map = [
            ("ORIGIN_COUNTRY", origin_countries),
            ("DESTINATION_COUNTRY", destination_countries),
            ("ORIGIN_PORT", origin_ports),
            ("DESTINATION_PORT", destination_ports),
            ("CONSIGNEE", consignees),
            ("CONSIGNOR", consignors),
        ]

        for filter_name, values in filter_map:
            if values:
                advance_search.append({
                    "FILTER": filter_name,
                    "VALUES": [v.upper() for v in values[:5]],
                    "OPERATOR": "AND",
                })

        if advance_search:
            payload["AdvanceSearch"] = advance_search

        return payload

    @staticmethod
    def build_summary_query(
        start_date: str | date,
        end_date: str | date,
        trade_type: str,
        trade_country: str,
        hs_codes: list[int] | None = None,
        products: list[str] | None = None,
        origin_countries: list[str] | None = None,
        destination_countries: list[str] | None = None,
        exclude: str | None = None,
        page_size: int = 1000,
        page_no: int = 1,
    ) -> dict:
        """Build payload for importer/exporter summary endpoints."""
        if isinstance(start_date, date):
            start_date = start_date.isoformat()
        if isinstance(end_date, date):
            end_date = end_date.isoformat()

        payload: dict = {
            "DateRange": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "TradeType": trade_type.upper(),
            "TradeCountry": trade_country.upper(),
            "page_size": min(page_size, 1000),
            "page_no": page_no,
        }

        if hs_codes:
            payload["PrimarySearch"] = {
                "FILTER": "HS_CODE",
                "VALUES": [str(c).zfill(4) if c < 1000 else str(c) for c in hs_codes][:5],
                "SearchType": "CONTAIN",
            }
        elif products:
            payload["PrimarySearch"] = {
                "FILTER": "PRODUCT",
                "VALUES": products[:5],
                "SearchType": "CONTAIN",
            }

        advance_search = []
        if origin_countries:
            advance_search.append({
                "FILTER": "ORIGIN_COUNTRY",
                "VALUES": [c.upper() for c in origin_countries[:5]],
                "OPERATOR": "AND",
            })
        if destination_countries:
            advance_search.append({
                "FILTER": "DESTINATION_COUNTRY",
                "VALUES": [c.upper() for c in destination_countries[:5]],
                "OPERATOR": "AND",
            })

        if advance_search:
            payload["AdvanceSearch"] = advance_search

        if exclude:
            payload["exclude"] = exclude

        return payload
