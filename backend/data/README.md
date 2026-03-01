# Backend data directory

- **targets.txt** — List of targets for batch scanning (one per line). Blank lines and lines starting with `#` are ignored. Use domain names or full URLs (e.g. `example.com`, `https://example.org`).
- **scans.jsonl** — Append-only JSONL of scan results (one JSON object per line). Created by `POST /api/scan` and by `batch_scan.py`.
- **scans.csv** — Flattened scan results for analysis. Maintained by `batch_scan.py`.
- **failures.jsonl** — Targets that failed (502/504/network). One JSON object per line: `target`, `error`, `status_code`, `timestamp`.

Do not commit `scans.jsonl`, `scans.csv`, or `failures.jsonl` if they contain sensitive targets (see `.gitignore`).
