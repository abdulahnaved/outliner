# outliner — static UI demo

Two routes:

- `/` landing page (single long page with anchored sections)
- `/report/demo` demo report page (dummy data)

## Local dev (frontend)

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Backend (FastAPI)

From repo root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Optional: set `OUTLINER_ALLOW_LOCALHOST=true` to allow scanning localhost/lab targets.

## Batch scan (Phase 3)

Passive-only data collection: run `POST /api/scan` for each target in `backend/data/targets.txt` with rate limiting. No crawling; only headers/TLS metadata are stored, not page content. Keep delay ≥ 1 second.

1. Start the backend (see above).
2. Edit `backend/data/targets.txt` (one target per line; blank and `#` lines ignored).
3. Run:

```bash
cd backend
source .venv/bin/activate
python scripts/batch_scan.py --limit 5
```

Options: `--api-url`, `--targets`, `--out-jsonl`, `--out-csv`, `--delay` (default 1.0), `--limit`, `--resume` (skip targets already in out-jsonl by normalized_host). Results append to `backend/data/scans.jsonl` and `backend/data/scans.csv`; failures go to `backend/data/failures.jsonl`.

