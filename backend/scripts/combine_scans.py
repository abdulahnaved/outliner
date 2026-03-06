#!/usr/bin/env python3
"""
Combine multiple cleaned scan JSONL files into one dataset.
Output: scans.v3_combined.cleaned.jsonl and scans.v3_combined.cleaned.csv.
Use after: clean_scans_jsonl.py for each of v3 and v3_extra.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Reuse clean script's CSV layout so combined CSV matches cleaned single-run CSVs
from clean_scans_jsonl import CSV_FIELDS, record_to_csv_row


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Combine cleaned scan JSONL files into one dataset")
    ap.add_argument(
        "inputs",
        type=Path,
        nargs="+",
        help="Cleaned JSONL paths (e.g. data/scans.v3.cleaned.jsonl data/scans.v3_extra.cleaned.jsonl)",
    )
    ap.add_argument("--out-jsonl", type=Path, default=None, help="Output JSONL (default: data/scans.v3_combined.cleaned.jsonl)")
    ap.add_argument("--out-csv", type=Path, default=None, help="Output CSV (default: same stem as out-jsonl with .csv)")
    ap.add_argument("--no-csv", action="store_true", help="Do not write CSV")
    args = ap.parse_args()

    combined: list[dict] = []
    for p in args.inputs:
        path = p.resolve()
        if not path.exists():
            alt = DATA_DIR / path.name
            if alt.exists():
                path = alt
            else:
                print(f"File not found: {p}", file=sys.stderr)
                return 1
        rows = load_jsonl(path)
        combined.extend(rows)
        print(f"  {path.name}: {len(rows)} rows", file=sys.stderr)

    if args.out_jsonl is None:
        args.out_jsonl = DATA_DIR / "scans.v3_combined.cleaned.jsonl"
    else:
        args.out_jsonl = args.out_jsonl.resolve()
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with open(args.out_jsonl, "w") as f:
        for r in combined:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {args.out_jsonl} ({len(combined)} rows)", file=sys.stderr)

    if not args.no_csv:
        out_csv = args.out_csv or args.out_jsonl.with_suffix(".csv")
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in combined:
                w.writerow(record_to_csv_row(r))
        print(f"Wrote {out_csv}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
