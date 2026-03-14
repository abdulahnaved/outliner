# outliner — security report

Outliner scans a website and produces a security report: rule-based score, ML estimate, security profile (radar chart), and recommendations.

**Routes:**

- `/` — Landing page; run a scan (domain input hits the backend).
- `/report?target=...` — Report page (scores, context, ML insight, security profile, recommendations, evidence).
- `/about` — What it is and how it works.

## Local dev

**Frontend**

```bash
npm install
npm run dev
```

Open http://localhost:3000.

**Backend (FastAPI)**

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

Run both (backend in one terminal, `npm run dev` in another) so the frontend can call the scan API.

## Testing

**Frontend (Jest)**

```bash
npm test
```

Runs unit tests for `lib/rules` (evaluateRules, buildCategorySummaries).

**Backend (pytest)**

```bash
cd backend
source .venv/bin/activate   # create/activate venv and pip install -r requirements.txt first
python -m pytest tests/ -v
```

Runs API tests (health, scan validation, SSRF) and scoring_v2 unit tests. No live HTTP requests.

## Batch scan

Passive-only data collection: run `POST /api/scan` for each target in `backend/data/targets.txt` with rate limiting.

1. Start the backend (see above).
2. Edit `backend/data/targets.txt` (one target per line; blank and `#` lines ignored).
3. Run:

```bash
cd backend
source .venv/bin/activate
python scripts/batch_scan.py --limit 5
```

Options: `--api-url`, `--targets`, `--out-jsonl`, `--out-csv`, `--delay` (default 1.0), `--limit`, `--resume`. Results append to `backend/data/scans.jsonl` and `backend/data/scans.csv`; failures go to `backend/data/failures.jsonl`.
