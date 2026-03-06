# Outliner lab — local Docker targets for passive scanning

Five Nginx containers with different security postures for testing headers, TLS, cookies, and CORS.

## Prerequisites

- Docker and Docker Compose
- Self-signed certs (see below)

## 1. Generate certificates

```bash
cd lab/certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout localhost.key -out localhost.crt \
  -subj "/CN=localhost"
cd ../..
```

## 2. Start lab targets

From repo root:

```bash
cd lab
docker compose up -d
```

| Service        | URL                     | Purpose                          |
|----------------|-------------------------|----------------------------------|
| lab_good       | https://localhost:8441  | HSTS, CSP, XFO, secure cookies   |
| lab_bad_headers| https://localhost:8442  | No CSP/XFO/nosniff               |
| lab_bad_cors   | https://localhost:8443  | Access-Control-Allow-Origin: *   |
| lab_bad_cookies| https://localhost:8444  | Cookie without Secure/HttpOnly   |
| lab_http_only  | http://localhost:8085   | HTTP only, no redirect            |

Browsers will show a self-signed certificate warning; accept for dev.

## 3. Sanity test (backend script)

With the lab up and backend deps installed:

```bash
cd backend
python scripts/test_lab.py
```

Prints status code and key headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, CORS, Set-Cookie) for each target. Uses `verify=False` for self-signed certs; dev only.

## 4. Scanning lab from the backend

By default the backend blocks localhost/private IPs (SSRF). To allow scanning these lab targets in dev, set:

```bash
export OUTLINER_ALLOW_LOCALHOST=true
```

Then run the FastAPI backend and use the frontend (or `POST /api/fetch`) with targets like `https://localhost:8441`. See `backend/.env.example`.

## 5. Batch scan (optional)

With the backend and lab running, add lab URLs to `backend/data/targets.txt` (uncomment the lab lines), set `OUTLINER_ALLOW_LOCALHOST=true`, then:

```bash
cd backend && source .venv/bin/activate
python scripts/batch_scan.py --limit 5
```

See root README for full batch scan options. Passive-only: no crawling; delay ≥ 1s; only headers/TLS metadata stored.

## Stop

```bash
cd lab
docker compose down
```
