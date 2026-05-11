"""Select the 10 highest and 10 lowest filings by `filings_average` from
processed JSONs (version_1), plus 2 additional filings per 0.1 bucket of
`filings_average` (0.1-0.2, 0.2-0.3, ...), and copy the corresponding raw
filings into `data/json_raw_lowest_highest/`.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nps_crawling.config import Config  # noqa: E402

VERSION = Config.PREPROCESSING_VERSION
PROCESSED_DIR = ROOT / "data" / "json_processed" / VERSION / "files"
RAW_DIR = ROOT / "data" / "json_raw" / "files"
OUT_DIR = ROOT / "data" / "json_raw_lowest_highest"

TOP_N = 10
BOTTOM_N = 10
PER_BUCKET = 2
BUCKET_EDGES = [round(0.1 * i, 1) for i in range(1, 11)]  # 0.1, 0.2, ..., 1.0


def extract_filings_average(path: Path) -> float | None:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        return None
    for record in data:
        meta = record.get("metadata", {}) if isinstance(record, dict) else {}
        for key in ("filings_average", "Filings Average", "filing_average"):
            if key in meta:
                return float(meta[key])
        if "filings_average" in record:
            return float(record["filings_average"])
    return None


def main() -> None:
    if not PROCESSED_DIR.is_dir():
        raise SystemExit(f"Processed dir not found: {PROCESSED_DIR}")
    if not RAW_DIR.is_dir():
        raise SystemExit(f"Raw dir not found: {RAW_DIR}")

    scored: list[tuple[str, float]] = []
    missing: list[str] = []
    for path in sorted(PROCESSED_DIR.glob("*.json")):
        try:
            avg = extract_filings_average(path)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"[skip] {path.name}: {e}")
            continue
        if avg is None:
            missing.append(path.name)
            continue
        scored.append((path.name, avg))

    if not scored:
        raise SystemExit("No filings_average values found in processed files.")

    scored.sort(key=lambda x: x[1])
    bottom = scored[:BOTTOM_N]
    top = scored[-TOP_N:][::-1]

    selected: dict[str, float] = {name: avg for name, avg in bottom + top}

    bucket_picks: list[tuple[float, float, list[tuple[str, float]]]] = []
    for i in range(len(BUCKET_EDGES) - 1):
        lo, hi = BUCKET_EDGES[i], BUCKET_EDGES[i + 1]
        in_bucket = [(n, a) for n, a in scored if lo <= a < hi and n not in selected]
        if not in_bucket:
            bucket_picks.append((lo, hi, []))
            continue
        if len(in_bucket) <= PER_BUCKET:
            picks = in_bucket
        else:
            step = len(in_bucket) / (PER_BUCKET + 1)
            idxs = [int(round(step * (k + 1))) for k in range(PER_BUCKET)]
            idxs = [min(max(0, j), len(in_bucket) - 1) for j in idxs]
            seen: set[int] = set()
            picks = []
            for j in idxs:
                if j in seen:
                    continue
                seen.add(j)
                picks.append(in_bucket[j])
        bucket_picks.append((lo, hi, picks))
        for n, a in picks:
            selected[n] = a

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    not_found_in_raw: list[str] = []
    for name in selected:
        src = RAW_DIR / name
        if not src.is_file():
            not_found_in_raw.append(name)
            continue
        shutil.copy2(src, OUT_DIR / name)
        copied += 1

    print(f"Scanned {len(scored)} processed filings.")
    if missing:
        print(f"  {len(missing)} had no filings_average (skipped).")
    bucket_total = sum(len(p) for _, _, p in bucket_picks)
    print(
        f"Selected {len(selected)} filings "
        f"({len(bottom)} lowest + {len(top)} highest + {bucket_total} bucketed)."
    )
    print(f"Copied {copied} files to {OUT_DIR}")
    if not_found_in_raw:
        print(f"  {len(not_found_in_raw)} not found in raw dir:")
        for n in not_found_in_raw:
            print(f"    {n}")

    print("\nLowest:")
    for name, avg in bottom:
        print(f"  {avg:.4f}  {name}")
    print("\nHighest:")
    for name, avg in top:
        print(f"  {avg:.4f}  {name}")
    print("\nBucketed:")
    for lo, hi, picks in bucket_picks:
        print(f"  [{lo:.1f}, {hi:.1f}): {len(picks)} picked")
        for name, avg in picks:
            print(f"    {avg:.4f}  {name}")


if __name__ == "__main__":
    main()
