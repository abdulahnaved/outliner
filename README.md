# outliner — security report

Outliner scans a website and produces a security report: rule-based score, ML estimate, security profile (radar chart), and recommendations.

## Repository layout

| Path | Purpose |
|------|---------|
| **`app/`** | Next.js App Router: pages, layouts, API routes (`app/api/*`). |
| **`components/`** | React UI (`Navbar`, `DomainInput`, `report/*` for the report page). |
| **`lib/`** | Shared TS: auth helpers, rules engine (`rules.ts`), report copy (`reportNarrative.ts`). |
| **`data/`** | Local SQLite (`outliner.db` when running the app) — **gitignored**. |
| **`backend/`** | FastAPI scanner: `main.py`, `services/` (passive scan, scoring, ML), `tests/`. |
| **`backend/scripts/`** | One-off Python tools (batch scan, dataset export, training helpers). See `backend/scripts/README.md`. |
| **`backend/data/`** | Target lists, validation assets, optional local datasets — see `backend/data/README.md`. |
| **`lab/`** | Docker/nginx test sites for local scanning. |

**Routes:**

- `/` — Landing page; **Run scan** goes to `/report?target=…` (single scan on the report page; backend must be running).
- `/report?target=...` — Live report (proxied through `POST /api/scan` to the Python backend).
- `/report?scanId=...` — Saved report (SQLite, signed-in users).
- `/login`, `/register` — Email + password auth (cookie session).
- `/dashboard` — Signed-in workspace (scan, recent saves, compare).
- `/history` — Full archive of saved scans.
- `/history/compare` — Compare two saved scans (query `a`, `b`).
- `/about` — What it is and how it works.

**Auth / persistence (Next.js):** SQLite under `data/outliner.db` (gitignored). Set `OUTLINER_AUTH_SECRET` (16+ chars) in production—see `.env.example`. The Python scanner is unchanged; only the Next app stores history.

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

Run both (backend in one terminal, `npm run dev` in another). The frontend calls `POST /api/scan`, which proxies to the Python backend (default `http://localhost:8000`; override with `OUTLINER_SCANNER_URL`).

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
