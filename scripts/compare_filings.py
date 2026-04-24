from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE = SCRIPT_DIR / "filings_summary.xlsx"
REFERENCE = SCRIPT_DIR / "filings_summary_same.xlsx"
OUTPUT = SCRIPT_DIR / "filings_summary_diff.xlsx"

MAX_ROWS: int | None = 250

source_wb = load_workbook(SOURCE)
source_ws = source_wb.active
sheet_name = source_ws.title

source_df = pd.read_excel(SOURCE, sheet_name=sheet_name)
reference_df = pd.read_excel(REFERENCE)

reference_urls = set(reference_df["filing_url"].dropna().astype(str))
diff_df = source_df[~source_df["filing_url"].astype(str).isin(reference_urls)]
diff_df = diff_df[source_df.columns]

if MAX_ROWS is not None:
    diff_df = diff_df.head(MAX_ROWS)

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    diff_df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Wrote {len(diff_df)} rows to {OUTPUT}")
