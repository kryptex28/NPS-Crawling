"""Normalize raw crawler parquet records for the preprocessing pipeline."""


def normalize_record(record: dict) -> dict:
    """Convert a parquet row to the shape expected by cleaning/filtering.

    Accepts:
    - **Raw (BetterSpider)**: keys like filing_*, core_text, keyword.
    - **Legacy flat**: company, ticker, cik, filing_url, keywords_found, html_text.

    Returns a dict with exactly: company, ticker, cik, filing_url, keywords_found, html_text.
    """
    if "html_text" in record and "company" in record:
        # Already in flat shape (legacy or pre-normalized)
        return {
            "company": record.get("company", ""),
            "ticker": record.get("ticker", "N/A"),
            "cik": record.get("cik", ""),
            "filing_url": record.get("filing_url", ""),
            "keywords_found": record.get("keywords_found", ""),
            "html_text": record.get("html_text", ""),
        }

    if "core_text" in record and "filing_ciks" in record:
        # Raw from BetterSpider: filing_* + core_text + keyword
        cik = _first_part(record.get("filing_ciks"))
        adsh = (record.get("filing_adsh") or "").replace("-", "")
        file_path = record.get("filing_file_path_name") or ""
        filing_url = ""
        if cik and adsh and file_path:
            filing_url = f"https://sec.gov/Archives/edgar/data/{cik}/{adsh}/{file_path}"
        company = _first_part(record.get("filing_display_names")) or "Unknown"
        return {
            "company": company,
            "ticker": "N/A",
            "cik": cik,
            "filing_url": filing_url,
            "keywords_found": record.get("keyword") or "",
            "html_text": record.get("core_text") or "",
        }

    # Fallback: return empty flat shape so downstream does not crash
    return {
        "company": "",
        "ticker": "N/A",
        "cik": "",
        "filing_url": "",
        "keywords_found": "",
        "html_text": record.get("core_text") or record.get("html_text") or "",
    }


def _first_part(value: str | None) -> str:
    """First segment when split by '; ' (used for list fields stored as strings)."""
    if not value or not isinstance(value, str):
        return ""
    part = value.split("; ")[0].strip()
    return part
