#!/usr/bin/env python3
"""
Lightweight external validation of scoring_v2 against Mozilla HTTP Observatory.

This script:
1. Loads our canonical dataset (scans.v3_combined.cleaned.jsonl) and reads v2 scores.
2. Queries Mozilla Observatory for a fixed sample of domains.
3. Builds a comparison table: our_score/grade vs mozilla_score/grade.
4. Writes:
   - data/validation/mozilla_comparison.csv
   - data/validation/mozilla_comparison_summary.txt
   - data/validation/mozilla_score_scatter.png
   - data/validation/mozilla_grade_distribution.png
5. Prints a short terminal summary (alignment stats and top mismatches).

NOTE: This is a validation experiment only; it DOES NOT modify scoring_v2, datasets, or models.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VALIDATION_DIR = DATA_DIR / "validation"
CANONICAL_JSONL = PROCESSED_DIR / "scans.v3_combined.cleaned.jsonl"

PREFERRED_SAMPLE_DOMAINS = [
    "google.com",
    "github.com",
    "wikipedia.org",
    "mozilla.org",
    "cloudflare.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "linkedin.com",
    "amazon.com",
    "nytimes.com",
    "bbc.com",
    "reuters.com",
    "etsy.com",
    "stackoverflow.com",
    "microsoft.com",
    "apple.com",
    "gov.uk",
    "bund.de",
    "aarhus.dk",
    "ucv.cl",
    "baja.hu",
]

# Mozilla Observatory (legacy) was sunset Oct 2024.
# MDN HTTP Observatory v2 API (current):
#   POST https://observatory-api.mdn.mozilla.net/api/v2/scan?host=<domain>
OBS_SCAN_V2_URL = "https://observatory-api.mdn.mozilla.net/api/v2/scan"


@dataclass
class OurScores:
    domain: str
    in_dataset: bool
    rule_score_v2: Optional[float]
    rule_grade_v2: Optional[str]
    rule_label_v2: Optional[int]
    rule_reasons_v2: List[str]


@dataclass
class MozillaScores:
    domain: str
    mozilla_score: Optional[float]
    mozilla_grade: Optional[str]
    mozilla_status_code: Optional[int] = None
    error: Optional[str] = None


GRADE_ORDER = [
    "F",
    "D-",
    "D",
    "D+",
    "C-",
    "C",
    "C+",
    "B-",
    "B",
    "B+",
    "A-",
    "A",
    "A+",
]
GRADE_INDEX = {g: i for i, g in enumerate(GRADE_ORDER)}


def load_canonical_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def normalize_host(host: str) -> str:
    h = (host or "").strip().lower()
    if h.endswith("."):
        h = h[:-1]
    return h


def build_our_scores(rows: List[Dict[str, Any]]) -> Dict[str, OurScores]:
    by_host: Dict[str, OurScores] = {}
    for r in rows:
        host = normalize_host(r.get("normalized_host") or "")
        if not host:
            continue
        our = OurScores(
            domain=host,
            in_dataset=True,
            rule_score_v2=r.get("rule_score_v2"),
            rule_grade_v2=r.get("rule_grade_v2"),
            rule_label_v2=r.get("rule_label_v2"),
            rule_reasons_v2=r.get("rule_reasons_v2") or [],
        )
        # Prefer latest occurrence if duplicates; dataset is already deduped, so this is mostly defensive.
        by_host[host] = our
    return by_host


def _coerce_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def select_stratified_domains(
    host_map: Dict[str, OurScores],
    *,
    top_n: int,
    mid_n: int,
    bottom_n: int,
) -> List[Tuple[str, str]]:
    """
    Select domains from canonical dataset by our_score_v2:
      - top_n highest
      - bottom_n lowest
      - mid_n around the median (closest absolute distance to median)

    Returns list of (domain, sample_group) tuples.
    """
    scored: List[Tuple[str, float]] = []
    for host, s in host_map.items():
        v = _coerce_float(s.rule_score_v2)
        if v is None:
            continue
        scored.append((host, v))
    if not scored:
        return []
    scored.sort(key=lambda x: x[1])
    scores_only = [v for _, v in scored]
    med = float(statistics.median(scores_only))

    bottom = scored[:bottom_n]
    top = scored[-top_n:] if top_n > 0 else []
    # Pick mid points closest to median, excluding those already selected.
    selected_hosts = {h for h, _ in bottom} | {h for h, _ in top}
    mid_candidates = [(h, v, abs(v - med)) for h, v in scored if h not in selected_hosts]
    mid_candidates.sort(key=lambda t: t[2])
    mid = [(h, v) for h, v, _ in mid_candidates[:mid_n]]

    out: List[Tuple[str, str]] = []
    for h, _ in top[::-1]:
        out.append((h, "top"))
    for h, _ in mid:
        out.append((h, "middle"))
    for h, _ in bottom:
        out.append((h, "bottom"))
    return out


def lookup_our_scores(host_map: Dict[str, OurScores], domain: str) -> OurScores:
    dom_norm = normalize_host(domain)
    candidates = [dom_norm]
    if dom_norm.startswith("www."):
        candidates.append(dom_norm[4:])
    else:
        candidates.append("www." + dom_norm)

    for c in candidates:
        if c in host_map:
            return host_map[c]
    # Not in dataset
    return OurScores(
        domain=dom_norm,
        in_dataset=False,
        rule_score_v2=None,
        rule_grade_v2=None,
        rule_label_v2=None,
        rule_reasons_v2=[],
    )


def call_mozilla_observatory(domain: str, *, timeout: float = 30.0) -> MozillaScores:
    """
    Query MDN HTTP Observatory v2 API for a domain.

    Endpoint:
      POST https://observatory-api.mdn.mozilla.net/api/v2/scan?host=<domain>

    Successful response includes score + grade directly (no polling required).
    """
    params = {"host": domain}
    try:
        resp = requests.post(OBS_SCAN_V2_URL, params=params, timeout=timeout)
    except Exception as e:
        return MozillaScores(domain=domain, mozilla_score=None, mozilla_grade=None, error=f"scan error: {e}")

    if resp.status_code != 200:
        return MozillaScores(domain=domain, mozilla_score=None, mozilla_grade=None, error=f"scan HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception as e:
        return MozillaScores(domain=domain, mozilla_score=None, mozilla_grade=None, error=f"scan JSON error: {e}")

    # Error shape: {"error": "...", "message": "..."}
    if isinstance(data, dict) and data.get("error"):
        msg = data.get("message") or data.get("error")
        # Sometimes status_code is included even on error.
        status_code = data.get("status_code") if isinstance(data, dict) else None
        try:
            status_i = int(status_code) if status_code is not None else None
        except (TypeError, ValueError):
            status_i = None
        return MozillaScores(domain=domain, mozilla_score=None, mozilla_grade=None, mozilla_status_code=status_i, error=str(msg))

    score = data.get("score") if isinstance(data, dict) else None
    grade = data.get("grade") if isinstance(data, dict) else None
    status_code = data.get("status_code") if isinstance(data, dict) else None
    try:
        score_f = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_f = None
    grade_str = str(grade).strip().upper() if grade is not None else None
    try:
        status_i = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        status_i = None
    return MozillaScores(domain=domain, mozilla_score=score_f, mozilla_grade=grade_str, mozilla_status_code=status_i)


def _mozilla_is_usable(m: MozillaScores) -> bool:
    """Only treat Mozilla result as comparable when scan succeeded for a real page."""
    if m.mozilla_score is None or not m.mozilla_grade:
        return False
    if m.mozilla_status_code is None:
        return True
    # Exclude common WAF/blocked/failed signals.
    return m.mozilla_status_code not in (0, 401, 403, 405, 408, 409, 429, 500, 502, 503, 504)


def grade_band_index(grade: Optional[str]) -> Optional[int]:
    if not grade:
        return None
    g = grade.strip().upper()
    return GRADE_INDEX.get(g)


def band_difference(our_grade: Optional[str], moz_grade: Optional[str]) -> str:
    i_our = grade_band_index(our_grade)
    i_moz = grade_band_index(moz_grade)
    if i_our is None or i_moz is None:
        return "missing"
    diff = abs(i_our - i_moz)
    if diff == 0:
        return "same_band"
    if diff == 1:
        return "±1_band"
    return "≥2_bands"


def ensure_validation_dir() -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def build_plots(rows: List[Dict[str, Any]], *, out_prefix: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots.", file=sys.stderr)
        return

    # Scatter: our_score vs mozilla_score
    xs: List[float] = []
    ys: List[float] = []
    for r in rows:
        os = r.get("our_score")
        ms = r.get("mozilla_score")
        if os is None or ms is None:
            continue
        try:
            xs.append(float(os))
            ys.append(float(ms))
        except (TypeError, ValueError):
            continue
    if xs and ys:
        fig, ax = plt.subplots()
        ax.scatter(xs, ys, alpha=0.7)
        ax.set_xlabel("Our rule_score_v2")
        ax.set_ylabel("Mozilla Observatory score")
        ax.set_title("Our score vs Mozilla score")
        ax.grid(True, alpha=0.3)
        path = VALIDATION_DIR / f"{out_prefix}_score_scatter.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {path}", file=sys.stderr)

    # Grade comparison bar chart
    our_counts: Dict[str, int] = {}
    moz_counts: Dict[str, int] = {}
    for r in rows:
        og = (r.get("our_grade") or "").strip().upper()
        mg = (r.get("mozilla_grade") or "").strip().upper()
        if og:
            our_counts[og] = our_counts.get(og, 0) + 1
        if mg:
            moz_counts[mg] = moz_counts.get(mg, 0) + 1

    grades_sorted = [g for g in GRADE_ORDER if g in our_counts or g in moz_counts]
    if grades_sorted:
        ours = [our_counts.get(g, 0) for g in grades_sorted]
        mozs = [moz_counts.get(g, 0) for g in grades_sorted]
        x = range(len(grades_sorted))
        width = 0.35
        fig, ax = plt.subplots()
        ax.bar([i - width / 2 for i in x], ours, width, label="Our v2")
        ax.bar([i + width / 2 for i in x], mozs, width, label="Mozilla")
        ax.set_xticks(list(x))
        ax.set_xticklabels(grades_sorted)
        ax.set_ylabel("Count")
        ax.set_title("Grade distribution: our v2 vs Mozilla")
        ax.legend()
        path = VALIDATION_DIR / f"{out_prefix}_grade_distribution.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {path}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare our scoring_v2 against MDN HTTP Observatory (v2 API)")
    ap.add_argument("--mode", choices=["preferred", "stratified"], default="preferred", help="Domain sampling mode")
    ap.add_argument("--top", type=int, default=20, help="Top-N domains by our_score_v2 (stratified mode)")
    ap.add_argument("--middle", type=int, default=20, help="Middle-N (closest to median) (stratified mode)")
    ap.add_argument("--bottom", type=int, default=20, help="Bottom-N domains by our_score_v2 (stratified mode)")
    ap.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout per request (seconds)")
    ap.add_argument("--out-prefix", type=str, default="mozilla", help="Output file prefix in data/validation/")
    ap.add_argument("--mismatch-reasons", type=int, default=5, help="How many top v2 reasons to print for mismatches")
    args = ap.parse_args()

    ensure_validation_dir()

    rows = load_canonical_rows(CANONICAL_JSONL)
    host_map = build_our_scores(rows)

    comparison_rows: List[Dict[str, Any]] = []
    if args.mode == "preferred":
        domain_groups = [(d, "preferred") for d in PREFERRED_SAMPLE_DOMAINS]
    else:
        domain_groups = select_stratified_domains(host_map, top_n=args.top, mid_n=args.middle, bottom_n=args.bottom)

    domains = [d for d, _ in domain_groups]
    print(f"Running Mozilla comparison for {len(domains)} domains (mode={args.mode})...", file=sys.stderr)

    for domain, group in domain_groups:
        our = lookup_our_scores(host_map, domain)
        moz = call_mozilla_observatory(domain, timeout=args.timeout)
        diff_band = band_difference(our.rule_grade_v2, moz.mozilla_grade)
        try:
            if our.rule_score_v2 is not None and moz.mozilla_score is not None:
                score_diff = float(our.rule_score_v2) - float(moz.mozilla_score)
            else:
                score_diff = None
        except (TypeError, ValueError):
            score_diff = None

        row = {
            "domain": domain,
            "sample_group": group,
            "in_dataset": int(our.in_dataset),
            "our_score": our.rule_score_v2,
            "our_grade": our.rule_grade_v2,
            "our_label": our.rule_label_v2,
            "our_reasons_top": " | ".join((our.rule_reasons_v2 or [])[: args.mismatch_reasons]),
            "mozilla_score": moz.mozilla_score,
            "mozilla_grade": moz.mozilla_grade,
            "mozilla_status_code": moz.mozilla_status_code,
            "score_difference": score_diff,
            "grade_difference_band": diff_band,
            "mozilla_error": moz.error,
        }
        comparison_rows.append(row)

    csv_path = VALIDATION_DIR / f"{args.out_prefix}_comparison.csv"
    write_csv(comparison_rows, csv_path)
    print(f"Wrote {csv_path}", file=sys.stderr)

    # Summary stats
    # Comparable subset: only rows where Mozilla returned a usable scan (not blocked/failed).
    usable = []
    for r in comparison_rows:
        m = MozillaScores(
            domain=r["domain"],
            mozilla_score=r.get("mozilla_score"),
            mozilla_grade=r.get("mozilla_grade"),
            mozilla_status_code=r.get("mozilla_status_code"),
            error=r.get("mozilla_error"),
        )
        if _mozilla_is_usable(m):
            usable.append(r)

    both_scores = [r for r in usable if r["our_score"] is not None and r["mozilla_score"] is not None]
    both_grades = [r for r in usable if r["our_grade"] and r["mozilla_grade"]]

    score_diffs = [float(r["score_difference"]) for r in both_scores if r["score_difference"] is not None]
    same_band = sum(1 for r in both_grades if r["grade_difference_band"] == "same_band")
    within_1 = sum(1 for r in both_grades if r["grade_difference_band"] in ("same_band", "±1_band"))
    big_mismatches = sum(1 for r in both_grades if r["grade_difference_band"] == "≥2_bands")

    n_domains = len(domains)
    n_usable = len(usable)
    n_both_scores = len(both_scores)
    n_both_grades = len(both_grades)

    mean_diff = statistics.mean(score_diffs) if score_diffs else None

    summary_lines: List[str] = []
    summary_lines.append("Mozilla comparison summary")
    summary_lines.append("==========================")
    summary_lines.append(f"Total domains in sample: {n_domains}")
    summary_lines.append(f"Domains with usable Mozilla scans: {n_usable}")
    summary_lines.append(f"Domains with both scores: {n_both_scores}")
    summary_lines.append(f"Domains with both grades: {n_both_grades}")
    if mean_diff is not None:
        summary_lines.append(f"Mean score_difference (our_score - mozilla_score): {mean_diff:.2f}")
    else:
        summary_lines.append("Mean score_difference: (no overlapping scores)")
    if n_both_grades > 0:
        same_pct = 100.0 * same_band / n_both_grades
        within1_pct = 100.0 * within_1 / n_both_grades
        big_pct = 100.0 * big_mismatches / n_both_grades
        summary_lines.append(f"same_band grades: {same_band}/{n_both_grades} ({same_pct:.1f}%)")
        summary_lines.append(f"within ±1 band: {within_1}/{n_both_grades} ({within1_pct:.1f}%)")
        summary_lines.append(f"≥2 band mismatches: {big_mismatches}/{n_both_grades} ({big_pct:.1f}%)")
    else:
        summary_lines.append("No overlapping grades to compare.")

    summary_path = VALIDATION_DIR / f"{args.out_prefix}_comparison_summary.txt"
    with summary_path.open("w") as f:
        f.write("\n".join(summary_lines) + "\n")
    print(f"Wrote {summary_path}", file=sys.stderr)

    # Plots
    build_plots(comparison_rows, out_prefix=args.out_prefix)

    # Terminal summary: basic table and mismatches
    print("\nDomains with both scores and grades:")
    header = f"{'domain':25} {'our_score':>9} {'our_grade':>8} {'moz_score':>10} {'moz_grade':>9} {'band_diff':>10}"
    print(header)
    print("-" * len(header))
    for r in comparison_rows:
        if r["our_score"] is None or r["mozilla_score"] is None:
            continue
        d = r["domain"]
        print(
            f"{d:25} "
            f"{(r['our_score'] if r['our_score'] is not None else ''):9.1f} "
            f"{(r['our_grade'] or ''):>8} "
            f"{(r['mozilla_score'] if r['mozilla_score'] is not None else ''):10.1f} "
            f"{(r['mozilla_grade'] or ''):>9} "
            f"{(r['grade_difference_band'] or ''):>10}"
        )

    # Top mismatches by band difference then by absolute score difference
    mismatches = [
        r for r in comparison_rows
        if r["grade_difference_band"] == "≥2_bands"
        and r["our_score"] is not None
        and r["mozilla_score"] is not None
    ]
    mismatches.sort(key=lambda r: abs(float(r["score_difference"])) if r["score_difference"] is not None else 0.0, reverse=True)

    print("\nTop ≥2-band mismatches (by absolute score difference) + our reasons:")
    if not mismatches:
        print("  None")
    else:
        for r in mismatches[:10]:
            reasons = r.get("our_reasons_top") or ""
            print(
                f"  {r['domain']}: our {r['our_score']} ({r['our_grade']}), "
                f"Mozilla {r['mozilla_score']} ({r['mozilla_grade']}), "
                f"diff={r['score_difference']}; reasons={reasons}"
            )

    # High-level alignment statement
    if n_both_grades > 0:
        within1_pct = 100.0 * within_1 / n_both_grades
        if within1_pct >= 70.0:
            verdict = "Our v2 scoring broadly aligns with Mozilla (most grades within ±1 band)."
        else:
            verdict = "Our v2 scoring differs noticeably from Mozilla for many sites."
        print(f"\nAlignment verdict: {verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

