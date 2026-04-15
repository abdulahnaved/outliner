"""
Score-context helper for the report page.

Loads the canonical processed dataset and provides:
- distribution_scores (rule_score values)
- dataset_median
- dataset_average
- percentile for a given score
"""
from __future__ import annotations

import json
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent
CANONICAL_DATASET = BACKEND_DIR / "data" / "processed" / "scans.v3_combined.cleaned.jsonl"
SAMPLED_DISTRIBUTION = BACKEND_DIR / "data" / "processed" / "rule_score_distribution.sample.json"


def _coerce_score(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


@lru_cache(maxsize=1)
def load_distribution_scores() -> list[float]:
    scores: list[float] = []
    if not CANONICAL_DATASET.exists():
        # Production deployments (Render) don't ship the full processed dataset.
        # Fall back to a small committed sample so percentile UI still works.
        if SAMPLED_DISTRIBUTION.exists():
            try:
                payload = json.loads(SAMPLED_DISTRIBUTION.read_text())
                raw = payload.get("scores", [])
                for v in raw:
                    s = _coerce_score(v)
                    if s is not None:
                        scores.append(s)
            except Exception:
                return scores
        return scores
    with open(CANONICAL_DATASET) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Prefer v2 (primary label set) for distribution/percentile
            score = _coerce_score(row.get("rule_score_v2")) or _coerce_score(row.get("rule_score"))
            if score is None:
                continue
            scores.append(score)
    return scores


def compute_percentile(distribution: list[float], score: float) -> Optional[float]:
    if not distribution:
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    below_or_equal = sum(1 for v in distribution if v <= s)
    return round((below_or_equal / len(distribution)) * 100.0, 2)


def get_score_context(current_rule_score: Optional[float]) -> dict:
    dist = load_distribution_scores()
    if not dist:
        return {
            "distribution_scores": [],
            "dataset_median": None,
            "dataset_average": None,
            "percentile": None if current_rule_score is None else None,
        }

    med = float(statistics.median(dist))
    avg = float(statistics.mean(dist))
    pct = None
    if current_rule_score is not None:
        pct = compute_percentile(dist, current_rule_score)

    return {
        "distribution_scores": dist,
        "dataset_median": round(med, 2),
        "dataset_average": round(avg, 2),
        "percentile": pct,
    }

