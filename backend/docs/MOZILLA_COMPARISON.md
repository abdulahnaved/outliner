## Mozilla Observatory comparison (lightweight external validation)

This experiment compares **Outliner scoring_v2** against **Mozilla HTTP Observatory** grades
for a small, hand-picked sample of well-known sites. The goal is purely qualitative:
to see whether our v2 grades are in roughly the same ballpark as Mozilla’s – **not**
to exactly replicate Mozilla’s scoring model.

### Method

- **Sample domains** (22 total), e.g.:
  - Large platforms: `google.com`, `github.com`, `wikipedia.org`, `mozilla.org`, `cloudflare.com`,
    `amazon.com`, `microsoft.com`, `apple.com`, `stackoverflow.com`.
  - Media / gov / misc: `nytimes.com`, `bbc.com`, `reuters.com`, `gov.uk`, `bund.de`, `aarhus.dk`.
  - Clearly weaker configs: `ucv.cl`, `baja.hu`, etc.
- **Our data source:** `data/processed/scans.v3_combined.cleaned.jsonl`.
  For each domain present in the dataset, we read:
  - `rule_score_v2`, `rule_grade_v2`, `rule_label_v2`, `rule_reasons_v2`.
- **Mozilla data source:** HTTP Observatory API:
  - `POST https://http-observatory.security.mozilla.org/api/v1/analyze?host=<domain>`
  - Poll `GET https://http-observatory.security.mozilla.org/api/v1/getScanResults?scan=<scan_id>`
  - Extract `score` and `grade` when available.
- **Comparison logic:**
  - `our_score` = `rule_score_v2` (0–110, category-capped, with bonuses).
  - `mozilla_score` = Observatory `score` (0–100).
  - `grade_difference_band` buckets:
    - `same_band`
    - `±1_band`
    - `≥2_bands`

Script used: `backend/scripts/compare_with_mozilla.py`.

### Results (current run)

Mozilla Observatory (legacy) was sunset in Oct 2024. This project now uses the **MDN HTTP Observatory v2 API**
for the external benchmark:

- `POST https://observatory-api.mdn.mozilla.net/api/v2/scan?host=<domain>`

Summary (from `data/validation/mozilla_comparison_summary.txt`):

- Total domains in sample: **22**
- Domains with both scores: **17**
- Domains with both grades: **17**
- Mean score difference (our_score − mozilla_score): **+4.00**
- same_band grades: **4/17 (23.5%)**
- within ±1 band: **9/17 (52.9%)**
- ≥2 band mismatches: **8/17 (47.1%)**

Outputs:

- CSV (per-domain comparison): `backend/data/validation/mozilla_comparison.csv`
- Summary text: `backend/data/validation/mozilla_comparison_summary.txt`
- Plots:
  - `backend/data/validation/mozilla_score_scatter.png`
  - `backend/data/validation/mozilla_grade_distribution.png`

### Interpretation

- On this sample, our v2 **roughly matches Mozilla’s numeric scores on average** (mean difference +4),
  but **grade alignment is only moderate** (about **53% within ±1 grade band**).
- The biggest disagreements are driven by policy differences:
  - Mozilla’s scoring includes checks and modifiers we don’t model (and vice versa).
  - Mozilla’s v2 scores can exceed 100 (bonus modifiers), similar to our v2 (0–110), but not identical.
- This is still useful as a *qualitative* external benchmark: it highlights which classes of sites
  get meaningfully different grades and are worth inspecting manually (e.g. `github.com` vs our CSP penalties).

### Known discrepancy: `moi.gov.iq`

During validation we found a concrete case where MDN HTTP Observatory and our scanner disagree,
and our own manual probes confirm that the **site itself is not the problem** – it is the
combination of gateway/WAF behaviour and which response a scanner happens to see:

- **Our scan / curl (browser-like UA, following redirects)**:
  - `http://moi.gov.iq` → 301 → `https://moi.gov.iq/`
  - `https://moi.gov.iq/` → 307 → `https://moi.gov.iq/verify/index.php?url=/`
  - Final `https://moi.gov.iq/verify/index.php?url=/` returns **200** with:
    - `content-security-policy: default-src 'self'; … require-trusted-types-for 'script';`
    - `strict-transport-security: max-age=31536000; includeSubDomains; preload`
    - `x-content-type-options: nosniff`
    - `referrer-policy: no-referrer`
    - `permissions-policy: geolocation=(), camera=(), microphone=(), interest-cohort=()`
  - Our `rule_score_v2` is 109 (A+) with only a cookie Secure weakness.

- **MDN HTTP Observatory (v2 API / web UI, same host):**
  - Reports **grade D, score 30/100**.
  - Claims: **CSP not implemented**, **HSTS not implemented**, **X-Content-Type-Options not implemented**,
    and “does not redirect to an HTTPS site”.

Given the curl trace above, MDN’s statements are only true for *some* responses – for example a
blocked/edge page (403) or a different redirect path/host variant – but not for the final 200
page that a normal browser sees. This illustrates a key limitation of cross-tool validation:

- Different scanners may receive **different HTTP responses** for the “same” host, depending on:
  - IP / region / bot detection / WAF.
  - Exact URL and redirect sequence.
  - User-Agent and other headers.
- As a result, statements like “no CSP” or “no HSTS” must be interpreted as
  **“not present on the response that *this* scanner evaluated”**, not as ground truth for the site.

In the thesis, these cases should be explicitly documented as **scanner disagreement** rather than
evidence that our feature extraction is wrong. Our v2 scoring and features for `moi.gov.iq` match
the headers observed via browser-like curl probes, while MDN appears to be grading a different
edge response.

### Known discrepancy: `kingcounty.gov` (MDN 0 vs our 38)

For the same host we see **MDN grade F, score 0/100** vs **our grade D, rule score 38**. Here we see
the **same** final response (both scanners see no CSP, no HSTS, cookies without Secure/HttpOnly/SameSite,
no Referrer-Policy, etc.); the gap is entirely due to **scoring design**, not which response was scanned.

**Why MDN gives 0**

MDN starts at 100 and applies **uncapped** penalties (HTTP Observatory modifiers):

| Test | Modifier | Notes |
|------|----------|--------|
| CSP not implemented | −25 | |
| Session cookie without Secure | −40 | Single heavy hit for session cookie over HTTP / no Secure |
| HSTS not implemented | −20 | |
| X-Frame-Options not implemented | −20 | |
| SRI: external scripts over HTTPS but no SRI | −5 | |
| X-Content-Type-Options not implemented | −5 | |

Total **−115** → score = max(0, 100 − 115) = **0**.

**Why we give 38 (D)**

- We use **category caps** (e.g. transport 25, content 25, cookies 20, browser 15, cross-origin 15).
  Penalties cannot pile up without bound.
- We do **not** model:
  - **X-Frame-Options** as a separate failing test (no −20 equivalent).
  - **X-Content-Type-Options** as a separate test (no −5).
  - **Subresource Integrity (SRI)** (we do not fetch or parse HTML for script tags).
- Cookie penalties are spread and capped under the cookies category (e.g. Secure, HttpOnly, SameSite),
  not a single −40 for “session cookie without Secure”.

So for the same set of missing headers and weak cookies, MDN’s uncapped sum drives the score to 0,
while our capped, category-based v2 leaves the site at 38 (D). This is a **deliberate design difference**:
we avoid letting one or two severe tests (e.g. session cookie + CSP + HSTS) wipe the entire score,
so the grade still reflects that HTTPS and redirect work and CORS is not wide open. If we wanted
closer alignment to MDN for sites like kingcounty.gov, we would need to either add X-Frame-Options /
X-Content-Type-Options / SRI and/or increase or uncap certain penalties (at the cost of more
sites clustering near 0).

