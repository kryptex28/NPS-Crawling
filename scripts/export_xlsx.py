"""Export processed JSON filings to XLSX summary."""

import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.utils import get_column_letter


"""
standalone script to export a XLSX file with context windows for manual classification
from the processed JSON files. run with python scripts/export_xlsx.py
only takes into account 1 context window for each filling. derives company name and ticker
from the "display_names" field in the filing metadata, which has the format:
"COMPANY NAME  (TICKER)  (CIK ...)"
"""

PROCESSED_BASE = Path(__file__).resolve().parent.parent / "data" / "json_processed"
VERSION = "version_1"
DATA_DIR = PROCESSED_BASE / VERSION / "files"
OUTPUT_PATH = PROCESSED_BASE / "filings_summary.xlsx"
MAX_ROWS = 500

# Requires "COMPANY NAME  (TICKER)  (CIK ...)" — two parenthesized groups
DISPLAY_NAME_RE = re.compile(r"^(.+?)\s*\(([^)]+)\)\s*\(CIK\s+[^)]+\)")


def parse_display_name(name: str):
    """Return (company_name, ticker) or None if format doesn't match."""
    m = DISPLAY_NAME_RE.match(name)
    if not m:
        return None
    company = m.group(1).strip()
    ticker = m.group(2).strip()
    return company, ticker


def collect_rows():
    rows = []
    seen_snippets = set()
    for json_path in sorted(DATA_DIR.glob("*.json")):
        with open(json_path, encoding="utf-8") as f:
            records = json.load(f)

        for record in records:
            filing = record.get("metadata", {}).get("filing", {})
            display_names = filing.get("display_names", [])
            if not display_names:
                continue

            parsed = parse_display_name(display_names[0])
            if parsed is None:
                continue  # weird display_name -> skip

            company_name, ticker = parsed
            cik = filing.get("ciks", [""])[0]
            filing_type = filing.get("file_type", "")
            filing_date = filing.get("file_date", "")
            url = record.get("url", "")

            # First context snippet, truncated
            contexts = record.get("context", [])
            snippet = ""
            if contexts:
                snippet = contexts[0].get("context", "")
                snippet = ILLEGAL_CHARACTERS_RE.sub("", snippet)

            if snippet in seen_snippets:
                continue
            seen_snippets.add(snippet)

            rows.append([
                company_name,
                ticker,
                cik,
                filing_type,
                filing_date,
                url,
                snippet,
            ])

            if len(rows) >= MAX_ROWS:
                return rows

    return rows


def main():
    rows = collect_rows()
    if not rows:
        print("No valid records found.")
        sys.exit(1)

    wb = Workbook()
    ws = wb.active
    ws.title = "Filings"

    headers = [
        "company_name",
        "ticker",
        "cik",
        "filing_type",
        "filing_date",
        "filing_url",
        "snippet_text_short",
    ]
    ws.append(headers)

    for row in rows:
        ws.append(row)

    # Auto-width (capped at 60)
    for col_idx, header in enumerate(headers, 1):
        max_len = len(header)
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value:
                    max_len = max(max_len, min(len(str(cell.value)), 60))
        ws.column_dimensions[get_column_letter(col_idx)].width = max_len + 2

    wb.save(OUTPUT_PATH)
    print(f"Saved {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
