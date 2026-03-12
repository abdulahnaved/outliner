#!/usr/bin/env python3
"""
Compute permutation feature importance for the best regression model
(Gradient Boosting Regressor trained on full dataset).

Retrains the model on the same train split (no saved model), then runs
sklearn's permutation_importance on the test set. Saves CSV, top-15 plot,
and a short thesis-friendly summary.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ML_DIR = BACKEND_DIR / "data" / "ml"
RESULTS_DIR = ML_DIR / "results"
PLOTS_DIR = RESULTS_DIR / "plots"

TRAIN_PATH = ML_DIR / "datasets" / "train_regression_full.csv"
TEST_PATH = ML_DIR / "datasets" / "test_regression_full.csv"

METADATA_COLUMNS = frozenset({"normalized_host"})
TARGET_COLUMN = "rule_score"


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path) as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        rows = list(r)
    return rows, fieldnames


def get_feature_columns(fieldnames: list[str]) -> list[str]:
    return [c for c in fieldnames if c not in METADATA_COLUMNS and c != TARGET_COLUMN]


def row_to_numeric(row: dict, feature_columns: list[str]) -> list[float]:
    out = []
    for col in feature_columns:
        v = row.get(col)
        if v is None or v == "":
            out.append(0.0)
            continue
        try:
            out.append(float(v))
        except (ValueError, TypeError):
            out.append(0.0)
    return out


def build_X_y(rows: list[dict], feature_columns: list[str]) -> tuple[list[list[float]], list[float]]:
    X = [row_to_numeric(r, feature_columns) for r in rows]
    y = []
    for r in rows:
        v = r.get(TARGET_COLUMN)
        if v is None or v == "":
            y.append(0.0)
            continue
        try:
            y.append(float(v))
        except (ValueError, TypeError):
            y.append(0.0)
    return X, y


def main() -> int:
    import numpy as np
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.inspection import permutation_importance

    if not TRAIN_PATH.exists() or not TEST_PATH.exists():
        print(f"Missing data: {TRAIN_PATH} or {TEST_PATH}", file=sys.stderr)
        return 1

    train_rows, fieldnames = load_csv(TRAIN_PATH)
    feature_columns = get_feature_columns(fieldnames)
    test_rows, _ = load_csv(TEST_PATH)

    X_train, y_train = build_X_y(train_rows, feature_columns)
    X_test, y_test = build_X_y(test_rows, feature_columns)

    X_train = np.asarray(X_train)
    X_test = np.asarray(X_test)
    y_train = np.asarray(y_train)
    y_test = np.asarray(y_test)

    # Same model as in train_regression_baseline.py (full dataset)
    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    # Permutation importance on test set
    perm = permutation_importance(
        model, X_test, y_test,
        n_repeats=20,
        scoring="r2",
        random_state=42,
    )

    # Build rows: feature_name, importance_mean, importance_std (sorted by mean desc)
    rows = []
    for i, name in enumerate(feature_columns):
        rows.append({
            "feature_name": name,
            "importance_mean": float(perm.importances_mean[i]),
            "importance_std": float(perm.importances_std[i]),
        })
    rows.sort(key=lambda r: -r["importance_mean"])

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # permutation_importance.csv
    out_csv = RESULTS_DIR / "permutation_importance.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["feature_name", "importance_mean", "importance_std"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_csv}", file=sys.stderr)

    # Top 15 bar chart with error bars
    top15 = rows[:15]
    names = [r["feature_name"] for r in top15]
    means = [r["importance_mean"] for r in top15]
    stds = [r["importance_std"] for r in top15]

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot.", file=sys.stderr)
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
        y_pos = range(len(names))
        ax.barh(y_pos, means, xerr=stds, align="center", capsize=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("importance_mean (R² drop when permuted)")
        ax.set_title("Permutation Feature Importance (Gradient Boosting)")
        ax.invert_yaxis()
        fig.savefig(PLOTS_DIR / "permutation_importance_top15.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Wrote {PLOTS_DIR / 'permutation_importance_top15.png'}", file=sys.stderr)

    # permutation_importance_summary.txt
    hsts_features = {"has_hsts", "hsts_max_age", "hsts_long", "hsts_include_subdomains", "hsts_preload", "hsts_max_age_days"}
    csp_features = {"has_csp", "csp_has_default_src", "csp_unsafe_inline", "csp_unsafe_eval", "csp_has_wildcard", "csp_has_object_none"}
    cookie_features = {"cookie_secure", "cookie_httponly", "cookie_samesite", "total_cookie_count", "secure_cookie_ratio", "httponly_cookie_ratio", "samesite_cookie_ratio"}

    top5 = rows[:5]
    hsts_in_top = [r for r in rows if r["feature_name"] in hsts_features][:5]
    csp_in_list = [r for r in rows if r["feature_name"] in csp_features]
    cookie_in_list = [r for r in rows if r["feature_name"] in cookie_features]
    header_like = [r for r in rows if "has_" in r["feature_name"] or "referrer" in r["feature_name"] or "server_header" in r["feature_name"] or "x_powered" in r["feature_name"]][:6]

    lines = [
        "Permutation feature importance — summary (Gradient Boosting, test set)",
        "=" * 60,
        "",
        "1. Highest permutation importance (top 5)",
    ]
    for r in top5:
        lines.append(f"   {r['feature_name']}: mean = {r['importance_mean']:.4f} (std = {r['importance_std']:.4f})")
    lines.append("")
    lines.append("2. HSTS features")
    if hsts_in_top:
        lines.append("   HSTS-related features remain among the most important by permutation.")
        for r in hsts_in_top[:3]:
            lines.append(f"   {r['feature_name']}: {r['importance_mean']:.4f}")
    else:
        lines.append("   No HSTS feature in the top 5; ranking may differ from impurity-based importance.")
    lines.append("")
    lines.append("3. CSP, cookie, and header features")
    if csp_in_list:
        lines.append("   CSP: " + ", ".join(f"{r['feature_name']} ({r['importance_mean']:.3f})" for r in csp_in_list[:4]))
    if cookie_in_list:
        lines.append("   Cookies: " + ", ".join(f"{r['feature_name']} ({r['importance_mean']:.3f})" for r in cookie_in_list[:4]))
    if header_like:
        lines.append("   Headers / policy: " + ", ".join(f"{r['feature_name']} ({r['importance_mean']:.3f})" for r in header_like[:4]))
    lines.append("")
    lines.append("Computed with sklearn permutation_importance, n_repeats=20, scoring='r2' on test set.")

    summary_path = RESULTS_DIR / "permutation_importance_summary.txt"
    with open(summary_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {summary_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
