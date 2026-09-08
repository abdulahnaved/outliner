# Running outliner with Docker

The full stack runs locally in three containers. No Node, Python, or Postgres
installation needed — only Docker.

## Quick start

```bash
docker compose up -d --build
```

| Service | URL | What it is |
|---|---|---|
| `web` | http://localhost:3000 | Next.js frontend + API gateway |
| `scanner` | http://localhost:8000/docs | FastAPI passive scanner |
| `db` | localhost:5432 | Postgres 16 |

First run takes 1–2 minutes (installing dependencies, building the Next.js
app). Subsequent runs are near-instant thanks to layer caching.

Tables are created automatically on the first database query — register an
account at `/register` to trigger it.

## Common commands

```bash
docker compose up -d --build     # start (rebuild images if code changed)
docker compose down              # stop and remove containers (data survives)
docker compose ps                # what's running
docker compose logs -f web       # follow one service's logs
docker compose restart web       # restart a single service

docker compose exec db psql -U outliner -d outliner    # psql shell
docker compose exec web sh                             # shell in the web container
docker compose exec web env                            # check env vars actually set
```

`--build` matters: compose reuses existing images unless told otherwise, so
without it your code changes won't appear.

## Architecture

```
browser → web (:3000) → scanner (:8000) → target website
             ↓
          db (:5432)
```

Matches the deployed topology (Vercel → Render → Neon), with each piece
running locally instead.

Containers reach each other by **service name** on the compose network:
`db:5432`, `scanner:8000`. Not `localhost` — inside a container that means
the container itself.

## Environment variables

Set in `docker-compose.yml` under the `web` service. No `.env` file is used;
the image deletes it during build so secrets never get baked in.

| Variable | Local value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://outliner:devpassword@db:5432/outliner` | No `?sslmode=require` — that's Neon-specific |
| `OUTLINER_SCANNER_URL` | `http://scanner:8000` | Service name, not localhost |
| `OUTLINER_AUTH_SECRET` | dev placeholder | Replace in any real deployment |
| `OUTLINER_AUTO_MIGRATE` | `"1"` | Runs the DDL in `lib/db.ts` on first connect |
| `PGSSLMODE` | `disable` | **Required locally** — see gotcha below |

### The PGSSLMODE gotcha

`lib/db.ts` enables SSL unless `PGSSLMODE=disable` is set:

```typescript
ssl: process.env.PGSSLMODE === 'disable' ? undefined : { rejectUnauthorized: false }
```

The default is correct for Neon, which requires SSL. The local Postgres
container doesn't support it, so without this variable every query fails and
the app returns a generic "Server error" with nothing in the logs.

Leave it unset when pointing at Neon or RDS.

## Data persistence

Postgres data lives in a named volume, not the container:

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data
```

So `docker compose down` keeps your data. To wipe it deliberately:

```bash
docker compose down -v      # -v also removes volumes
```

## Images

**`Dockerfile`** (repo root) — Next.js, three stages:

1. `deps` — `npm ci` in its own layer so it stays cached across code edits
2. `builder` — runs `next build`
3. `runner` — copies only `.next/standalone` and `.next/static`

Requires `output: 'standalone'` in `next.config.js`, which traces the import
graph and emits a pruned dependency tree with its own `server.js`
(370 MB → 26 MB). Note that `standalone` excludes `.next/static`, hence the
second COPY — without it the app serves HTML with every asset 404ing.

Runs as non-root (`nextjs`). `--chown` on the COPY lines is necessary because
Next writes a cache directory at runtime.

**`backend/Dockerfile`** — FastAPI, single stage. Debian `slim` rather than
Alpine: scientific Python wheels are built against glibc, and on Alpine pip
would compile numpy/scipy/scikit-learn from source.

Runs as non-root (`appuser`). No `--chown` needed — the scanner only reads.

`--host 0.0.0.0` in the CMD is required. Uvicorn's default of `127.0.0.1`
means "this machine only," which inside a container is unreachable from
anywhere else.

## Build contexts

Two `.dockerignore` files, because the two images build from different
directories:

| Context | Excludes |
|---|---|
| repo root | `node_modules/`, `.next/`, `.git/`, `.env`, `docs/`, `lab/` |
| `backend/` | `.venv/`, `__pycache__/`, `tests/`, `scripts/`, training data |

Root context: ~400 MB → 2 MB. Backend: → 921 KB.

The backend keeps `data/ml/artifacts/` (the five model files, ~800 KB) while
excluding the rest of `data/`. Docker won't descend into an excluded
directory, so re-inclusion has to be laddered one level at a time:

```dockerignore
data/*
!data/ml
data/ml/*
!data/ml/artifacts
```

Model artifacts are baked into the image rather than mounted, so the scanner
is self-contained. `requirements.txt` pins `scikit-learn==1.8.0` — the
`.joblib` files were saved by that version and are sensitive to mismatches.

## Requirements files

| File | Contents | Used by |
|---|---|---|
| `backend/requirements.txt` | 8 runtime packages, pinned | the image |
| `backend/requirements-dev.txt` | the above + matplotlib, pytest | local venv |

For local development: `pip install -r requirements-dev.txt`

## Scanning the lab containers

`utils/ssrf.py` blocks 172.16.0.0/12, which is where Docker's bridge network
lives. To scan `lab/` targets from the scanner container, set
`OUTLINER_ALLOW_LOCALHOST=true`. Local testing only.

## Troubleshooting

**"Server error" on register/login** — check `PGSSLMODE` reached the
container: `docker compose exec web env | grep PGSSLMODE`. Compose files nest
deeply and it's easy to land a variable in the wrong service.

**Web starts before Postgres is ready** — `depends_on` waits for the container
to start, not for Postgres to accept connections. `docker compose restart web`
clears it; a healthcheck on `db` would fix it properly.

**Code changes not appearing** — you forgot `--build`.

**Tables missing** — they're created on first query, not at startup. Hit
`/register` or any authenticated route.
