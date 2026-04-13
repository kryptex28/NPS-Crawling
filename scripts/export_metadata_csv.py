"""Export processed JSON filings to a CSV summary.

Run with:
    python scripts/export_csv.py

Configure FOLDER_NAMES below to select which preprocessing versions to include.
"""

import csv
import json
import sys
from pathlib import Path

PROCESSED_BASE = Path(__file__).resolve().parent.parent / "data" / "json_processed"
OUTPUT_PATH = Path(__file__).resolve().parent / "metadata_csv_exports" / "filings_summary.csv"

# --- Configure which folders under data/json_processed to include ---
FOLDER_NAMES = [
    "net_promoter",
    "nps",
]

CSV_COLUMNS = [
    "id",
    "ciks",
    "ticker",
    "period_ending",
    "display_names",
    "root_forms",
    "file_date",
    "form",
    "adsh",
    "file_type",
    "file_description",
    "file_num",
    "film_num",
    "keyword",
    "url",
    "similarity_threshold",
]


def _join_list(value):
    """Join list values with '; ' or return the scalar as string."""
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return str(value) if value is not None else ""


def read_similarity_threshold(folder_path: Path, folder_name: str) -> str:
    """Read similarity_threshold from the preprocessing summary JSON."""
    candidates = list(folder_path.glob(f"preprocessing_*.json"))
    for candidate in candidates:
        with open(candidate, encoding="utf-8") as f:
            data = json.load(f)
        threshold = data.get("experiment_setup", {}).get("similarity_threshold")
        if threshold is not None:
            return str(threshold)
    return ""


def main():
    rows = []

    for folder_name in FOLDER_NAMES:
        folder_path = PROCESSED_BASE / folder_name
        files_dir = folder_path / "files"

        if not files_dir.is_dir():
            print(f"WARNING: {files_dir} not found, skipping.", file=sys.stderr)
            continue

        threshold = read_similarity_threshold(folder_path, folder_name)

        for json_file in sorted(files_dir.glob("*.json")):
            with open(json_file, encoding="utf-8") as f:
                records = json.load(f)

            for record in records:
                filing = record.get("metadata", {}).get("filing", {})
                row = {
                    "id": filing.get("id", ""),
                    "ciks": _join_list(filing.get("ciks")),
                    "ticker": _join_list(filing.get("ticker")),
                    "period_ending": filing.get("period_ending", ""),
                    "display_names": _join_list(filing.get("display_names")),
                    "root_forms": _join_list(filing.get("root_forms")),
                    "file_date": filing.get("file_date", ""),
                    "form": filing.get("form", ""),
                    "adsh": filing.get("adsh", ""),
                    "file_type": filing.get("file_type", ""),
                    "file_description": filing.get("file_description", ""),
                    "file_num": _join_list(filing.get("file_num")),
                    "film_num": _join_list(filing.get("film_num")),
                    "keyword": filing.get("keyword", ""),
                    "url": record.get("url", ""),
                    "similarity_threshold": threshold,
                }
                rows.append(row)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
