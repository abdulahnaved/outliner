#!/usr/bin/env python3
"""
Train HistGradientBoostingRegressor (max_depth=5) on the full regression dataset,
evaluate on test, save metrics, predictions, permutation importance, plots,
and compare with the baseline GradientBoostingRegressor.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ML_DIR = BACKEND_DIR / "data" / "ml"
RESULTS_DIR = ML_DIR / "results"
PLOTS_DIR = RESULTS_DIR / "plots"
ARTIFACTS_DIR = ML_DIR / "artifacts"
MODEL_STEM = "hist_gradient_boosting_depth5"

TRAIN_PATH = ML_DIR / "datasets" / "train_regression_full.csv"
VAL_PATH = ML_DIR / "datasets" / "val_regression_full.csv"
TEST_PATH = ML_DIR / "datasets" / "test_regression_full.csv"

METADATA_COLUMNS = frozenset({"normalized_host"})
TARGET_COLUMN = "rule_score_v2"


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
    global TRAIN_PATH, VAL_PATH, TEST_PATH
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.inspection import permutation_importance

    for p in (TRAIN_PATH, VAL_PATH, TEST_PATH):
        if not p.exists():
            # Fallback if called before data/ml/datasets/ existed
            legacy = ML_DIR / p.name
            if legacy.exists():
                if p == TRAIN_PATH:
                    TRAIN_PATH = legacy
                elif p == VAL_PATH:
                    VAL_PATH = legacy
                else:
                    TEST_PATH = legacy
            else:
                print(f"Missing: {p}", file=sys.stderr)
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

    # HistGradientBoostingRegressor (deeper trees)
    model = HistGradientBoostingRegressor(
        max_depth=5,
        learning_rate=0.05,
        max_iter=300,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Save runtime artifacts for backend inference
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(model, ARTIFACTS_DIR / f"{MODEL_STEM}.joblib")
    with open(ARTIFACTS_DIR / f"{MODEL_STEM}_features.json", "w") as f:
        json.dump(feature_columns, f, indent=2)
    preprocessing = {
        "target_column": TARGET_COLUMN,
        "expected_feature_columns": feature_columns,
        "excluded_from_training": ["normalized_host", "rule_score", "rule_score_v2", "rule_grade", "rule_label", "rule_reasons", "csp_score", "tls_version_score"],
        "missing_value_handling": {
            "tls_version": "set to 0, add tls_version_missing=1",
            "certificate_days_left": "set to 0, add cert_days_missing=1",
            "cert_expired": "1 if certificate_days_left <= 0 else 0",
            "response_time_log": "log1p(response_time)",
        },
        "derived_columns": ["tls_version_missing", "cert_days_missing", "cert_expired", "response_time_log"],
    }
    with open(ARTIFACTS_DIR / f"{MODEL_STEM}_preprocessing.json", "w") as f:
        json.dump(preprocessing, f, indent=2)
    print(f"Wrote artifacts to {ARTIFACTS_DIR}", file=sys.stderr)

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # hist_gradient_boosting_depth5_metrics.json
    metrics = {
        "model": "HistGradientBoostingRegressor",
        "max_depth": 5,
        "learning_rate": 0.05,
        "max_iter": 300,
        "random_state": 42,
        "test_MAE": mae,
        "test_RMSE": rmse,
        "test_R2": r2,
    }
    with open(RESULTS_DIR / "hist_gradient_boosting_depth5_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("Wrote hist_gradient_boosting_depth5_metrics.json", file=sys.stderr)

    # hist_gradient_boosting_depth5_metrics.csv
    with open(RESULTS_DIR / "hist_gradient_boosting_depth5_metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "max_depth", "MAE", "RMSE", "R2"])
        w.writerow(["HistGradientBoostingRegressor_depth5", 5, mae, rmse, r2])
    print("Wrote hist_gradient_boosting_depth5_metrics.csv", file=sys.stderr)

    # hist_gradient_boosting_depth5_predictions.csv
    with open(RESULTS_DIR / "hist_gradient_boosting_depth5_predictions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["actual_score", "predicted_score"])
        for a, p in zip(y_test, y_pred):
            w.writerow([float(a), float(p)])
    print("Wrote hist_gradient_boosting_depth5_predictions.csv", file=sys.stderr)

    # Plots: actual vs predicted, residuals
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots.", file=sys.stderr)
    else:
        # Actual vs predicted
        fig, ax = plt.subplots()
        ax.scatter(y_test, y_pred, alpha=0.5)
        ax.plot([0, 110], [0, 110], "r--", label="y=x")
        ax.set_xlabel("actual rule_score_v2")
        ax.set_ylabel("predicted rule_score_v2")
        ax.set_title("HistGradientBoostingRegressor (max_depth=5) — Actual vs Predicted (v2)")
        ax.legend()
        ax.set_xlim(0, 110)
        ax.set_ylim(0, 110)
        fig.savefig(PLOTS_DIR / "actual_vs_predicted_hist_gradient_boosting_depth5.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("Wrote actual_vs_predicted_hist_gradient_boosting_depth5.png", file=sys.stderr)

        # Residuals
        residuals = y_test - y_pred
        fig, ax = plt.subplots()
        ax.scatter(y_pred, residuals, alpha=0.5)
        ax.axhline(0, color="r", linestyle="--")
        ax.set_xlabel("predicted_score")
        ax.set_ylabel("residual")
        ax.set_title("HistGradientBoostingRegressor (max_depth=5) — Residual plot")
        fig.savefig(PLOTS_DIR / "residuals_hist_gradient_boosting_depth5.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("Wrote residuals_hist_gradient_boosting_depth5.png", file=sys.stderr)

    # Permutation importance
    perm = permutation_importance(
        model, X_test, y_test,
        n_repeats=20,
        scoring="r2",
        random_state=42,
    )
    perm_rows = []
    for i, name in enumerate(feature_columns):
        perm_rows.append({
            "feature_name": name,
            "importance_mean": float(perm.importances_mean[i]),
            "importance_std": float(perm.importances_std[i]),
        })
    perm_rows.sort(key=lambda r: -r["importance_mean"])

    with open(RESULTS_DIR / "hist_gradient_boosting_depth5_permutation_importance.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["feature_name", "importance_mean", "importance_std"])
        w.writeheader()
        w.writerows(perm_rows)
    print("Wrote hist_gradient_boosting_depth5_permutation_importance.csv", file=sys.stderr)

    # Feature importance plot (top 15)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        pass
    else:
        top15 = perm_rows[:15]
        names = [r["feature_name"] for r in top15]
        means = [r["importance_mean"] for r in top15]
        stds = [r["importance_std"] for r in top15]
        fig, ax = plt.subplots(figsize=(8, 6))
        y_pos = range(len(names))
        ax.barh(y_pos, means, xerr=stds, align="center", capsize=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("importance_mean (R² drop when permuted)")
        ax.set_title("HistGradientBoostingRegressor (max_depth=5) — Top 15 permutation importance")
        ax.invert_yaxis()
        fig.savefig(PLOTS_DIR / "hist_gradient_boosting_depth5_feature_importance.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("Wrote hist_gradient_boosting_depth5_feature_importance.png", file=sys.stderr)

    # gradient_vs_hist_comparison.csv: load baseline from regression_results.json
    baseline_path = RESULTS_DIR / "regression_results.json"
    if not baseline_path.exists():
        print("regression_results.json not found; skipping comparison CSV.", file=sys.stderr)
    else:
        with open(baseline_path) as f:
            baseline = json.load(f)
        gb_test = baseline.get("models", {}).get("gradient_boosting_regressor", {}).get("test", {})
        gb_mae = gb_test.get("mae")
        gb_rmse = gb_test.get("rmse")
        gb_r2 = gb_test.get("r2")
        with open(RESULTS_DIR / "gradient_vs_hist_comparison.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["model", "MAE", "RMSE", "R2"])
            w.writerow(["GradientBoostingRegressor", gb_mae, gb_rmse, gb_r2])
            w.writerow(["HistGradientBoostingRegressor_depth5", mae, rmse, r2])
        print("Wrote gradient_vs_hist_comparison.csv", file=sys.stderr)

    print(f"\nHistGradientBoostingRegressor (max_depth=5) test: MAE={mae:.4f} RMSE={rmse:.4f} R²={r2:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
