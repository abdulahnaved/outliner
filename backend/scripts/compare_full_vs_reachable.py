#!/usr/bin/env python3
"""
Compare full-dataset vs reachable-only regression results.

Reads regression_results.json (full) and regression_results_reachable.json (reachable),
produces full_vs_reachable_comparison.json, full_vs_reachable_comparison.csv,
and reachable_model_summary.txt.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BACKEND_DIR / "data" / "ml" / "results"


def load_results(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> int:
    full_path = RESULTS_DIR / "regression_results.json"
    reachable_path = RESULTS_DIR / "regression_results_reachable.json"

    if not full_path.exists():
        print(f"Full results not found: {full_path}", file=sys.stderr)
        return 1
    if not reachable_path.exists():
        print(f"Reachable results not found: {reachable_path}. Run train_regression_baseline.py with --results-suffix reachable first.", file=sys.stderr)
        return 1

    full = load_results(full_path)
    reachable = load_results(reachable_path)

    model_names = ["linear_regression", "random_forest_regressor", "gradient_boosting_regressor"]
    comparison = {
        "full_dataset": {"train_samples": full.get("train_samples"), "val_samples": full.get("val_samples"), "test_samples": full.get("test_samples")},
        "reachable_only": {"train_samples": reachable.get("train_samples"), "val_samples": reachable.get("val_samples"), "test_samples": reachable.get("test_samples")},
        "models": {},
    }

    rows_csv = []
    for name in model_names:
        f = full.get("models", {}).get(name, {})
        r = reachable.get("models", {}).get(name, {})
        if not f or not r:
            continue
        f_val, f_test = f.get("val", {}), f.get("test", {})
        r_val, r_test = r.get("val", {}), r.get("test", {})

        delta_mae = r_test.get("mae", 0) - f_test.get("mae", 0)
        delta_rmse = r_test.get("rmse", 0) - f_test.get("rmse", 0)
        delta_r2 = r_test.get("r2", 0) - f_test.get("r2", 0)

        comparison["models"][name] = {
            "full": {"val_mae": f_val.get("mae"), "val_rmse": f_val.get("rmse"), "val_r2": f_val.get("r2"), "test_mae": f_test.get("mae"), "test_rmse": f_test.get("rmse"), "test_r2": f_test.get("r2")},
            "reachable": {"val_mae": r_val.get("mae"), "val_rmse": r_val.get("rmse"), "val_r2": r_val.get("r2"), "test_mae": r_test.get("mae"), "test_rmse": r_test.get("rmse"), "test_r2": r_test.get("r2")},
            "delta_test_mae": delta_mae,
            "delta_test_rmse": delta_rmse,
            "delta_test_r2": delta_r2,
        }
        rows_csv.append({
            "model": name,
            "full_val_mae": f_val.get("mae"),
            "full_val_rmse": f_val.get("rmse"),
            "full_val_r2": f_val.get("r2"),
            "full_test_mae": f_test.get("mae"),
            "full_test_rmse": f_test.get("rmse"),
            "full_test_r2": f_test.get("r2"),
            "reachable_val_mae": r_val.get("mae"),
            "reachable_val_rmse": r_val.get("rmse"),
            "reachable_val_r2": r_val.get("r2"),
            "reachable_test_mae": r_test.get("mae"),
            "reachable_test_rmse": r_test.get("rmse"),
            "reachable_test_r2": r_test.get("r2"),
            "delta_test_mae": delta_mae,
            "delta_test_rmse": delta_rmse,
            "delta_test_r2": delta_r2,
        })

    # Save comparison JSON
    out_json = RESULTS_DIR / "full_vs_reachable_comparison.json"
    with open(out_json, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"Wrote {out_json}", file=sys.stderr)

    # Save comparison CSV
    if rows_csv:
        out_csv = RESULTS_DIR / "full_vs_reachable_comparison.csv"
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows_csv[0].keys())
            w.writeheader()
            w.writerows(rows_csv)
        print(f"Wrote {out_csv}", file=sys.stderr)

    # Summary text: best reachable model, full vs reachable, whether difference justifies preference
    reachable_test_r2 = {name: reachable.get("models", {}).get(name, {}).get("test", {}).get("r2", 0) for name in model_names}
    best_reachable_name = max(reachable_test_r2, key=reachable_test_r2.get)
    best_reachable_r2 = reachable_test_r2[best_reachable_name]
    full_best_r2 = full.get("models", {}).get(best_reachable_name, {}).get("test", {}).get("r2", 0)
    delta_best_r2 = best_reachable_r2 - full_best_r2

    # Overall: did reachable improve or hurt? Use average test R² across models.
    full_avg_r2 = sum(full.get("models", {}).get(n, {}).get("test", {}).get("r2", 0) for n in model_names) / len(model_names)
    reachable_avg_r2 = sum(reachable.get("models", {}).get(n, {}).get("test", {}).get("r2", 0) for n in model_names) / len(model_names)
    avg_delta = reachable_avg_r2 - full_avg_r2

    summary_lines = [
        "Full vs reachable regression comparison — summary",
        "=" * 50,
        "",
        "1. Best model on reachable-only data",
        f"   Best model: {best_reachable_name} (test R² = {best_reachable_r2:.4f}).",
        "",
        "2. Reachable-only vs full-dataset performance",
        f"   On average across the three models, reachable-only test R² is {reachable_avg_r2:.4f} vs full-dataset {full_avg_r2:.4f} (delta = {avg_delta:+.4f}).",
        f"   For the best model ({best_reachable_name}), reachable test R² = {best_reachable_r2:.4f}, full test R² = {full_best_r2:.4f} (delta = {delta_best_r2:+.4f}).",
        "",
        "3. Conclusion",
    ]
    if abs(avg_delta) < 0.01:
        summary_lines.append("   The difference between full-dataset and reachable-only training is small (|delta R²| < 0.01). Either setup is acceptable; full-dataset uses more data and may generalize to blocked/unreachable hosts if needed.")
    elif avg_delta > 0:
        summary_lines.append("   Reachable-only training performs better on test metrics. Prefer reachable-only if the deployment population is restricted to reachable hosts and the slight loss of training data is acceptable.")
    else:
        summary_lines.append("   Full-dataset training performs better on test metrics. Prefer full-dataset unless there is a strong reason to exclude blocked/unreachable hosts from training.")
    summary_lines.append("")
    summary_lines.append("See full_vs_reachable_comparison.json and full_vs_reachable_comparison.csv for per-model metrics and deltas.")

    summary_path = RESULTS_DIR / "reachable_model_summary.txt"
    with open(summary_path, "w") as f:
        f.write("\n".join(summary_lines))
    print(f"Wrote {summary_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
