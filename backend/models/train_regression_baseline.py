#!/usr/bin/env python3
"""
Baseline regression models for predicting rule_score from raw security features.

Trains Linear Regression, Random Forest Regressor, and Gradient Boosting Regressor;
evaluates with MAE, RMSE, R²; saves metrics, predictions, feature importance,
plots, and error analysis to data/ml/results/.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ML_DIR = BACKEND_DIR / "data" / "ml"
RESULTS_DIR = ML_DIR / "results"
PLOTS_DIR = RESULTS_DIR / "plots"

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
    ap = argparse.ArgumentParser(description="Train regression baselines for rule_score")
    ap.add_argument("--train", type=Path, default=ML_DIR / "datasets" / "train_regression_full.csv", help="Train CSV")
    ap.add_argument("--val", type=Path, default=ML_DIR / "datasets" / "val_regression_full.csv", help="Val CSV")
    ap.add_argument("--test", type=Path, default=ML_DIR / "datasets" / "test_regression_full.csv", help="Test CSV")
    ap.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="Results directory")
    ap.add_argument("--results-suffix", type=str, default="", help="Suffix for output filenames (e.g. reachable -> regression_results_reachable.json)")
    args = ap.parse_args()

    suffix = (args.results_suffix or "").strip()
    file_suffix = f"_{suffix}" if suffix else ""

    def resolve(p: Path) -> Path:
        if p.exists():
            return p.resolve()
        # Fallback for legacy layout without datasets/ subdir
        alt = ML_DIR / p.name
        return alt.resolve() if alt.exists() else p.resolve()

    train_path = resolve(args.train)
    val_path = resolve(args.val)
    test_path = resolve(args.test)
    for name, p in [("train", train_path), ("val", val_path), ("test", test_path)]:
        if not p.exists():
            print(f"{name} not found: {p}", file=sys.stderr)
            return 1

    train_rows, fieldnames = load_csv(train_path)
    feature_columns = get_feature_columns(fieldnames)
    if not feature_columns:
        print("No feature columns.", file=sys.stderr)
        return 1

    val_rows, _ = load_csv(val_path)
    test_rows, _ = load_csv(test_path)

    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    X_train, y_train = build_X_y(train_rows, feature_columns)
    X_val, y_val = build_X_y(val_rows, feature_columns)
    X_test, y_test = build_X_y(test_rows, feature_columns)

    X_train = np.asarray(X_train)
    X_val = np.asarray(X_val)
    X_test = np.asarray(X_test)
    y_train = np.asarray(y_train)
    y_val = np.asarray(y_val)
    y_test = np.asarray(y_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_suffix": suffix or "full",
        "train_samples": len(y_train),
        "val_samples": len(y_val),
        "test_samples": len(y_test),
        "n_features": len(feature_columns),
        "feature_columns": feature_columns,
        "models": {},
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    def eval_metrics(y_true, y_pred):
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2": float(r2_score(y_true, y_pred)),
        }

    stored_preds = {}
    models_to_train = [
        ("linear_regression", LinearRegression(), X_train_scaled, X_val_scaled, X_test_scaled, True),
        ("random_forest_regressor", RandomForestRegressor(random_state=42), X_train, X_val, X_test, False),
        ("gradient_boosting_regressor", GradientBoostingRegressor(random_state=42), X_train, X_val, X_test, False),
    ]

    try:
        import xgboost as xgb
        models_to_train.append(("xgboost_regressor", xgb.XGBRegressor(random_state=42), X_train, X_val, X_test, False))
    except ImportError:
        pass

    for model_name, model, X_tr, X_va, X_te, _ in models_to_train:
        model.fit(X_tr, y_train)
        val_pred = model.predict(X_va)
        test_pred = model.predict(X_te)
        results["models"][model_name] = {
            "val": eval_metrics(y_val, val_pred),
            "test": eval_metrics(y_test, test_pred),
        }
        stored_preds[model_name] = test_pred
        if hasattr(model, "coef_"):
            results["models"][model_name]["feature_importance"] = dict(zip(feature_columns, [float(x) for x in model.coef_]))
        elif hasattr(model, "feature_importances_"):
            results["models"][model_name]["feature_importance"] = dict(zip(feature_columns, [float(x) for x in model.feature_importances_]))

        # Predictions CSV
        pred_path = args.out_dir / f"predictions_{model_name}{file_suffix}.csv"
        with open(pred_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["normalized_host", "actual_rule_score_v2", "predicted_rule_score_v2", "absolute_error"])
            for r, actual, pred in zip(test_rows, y_test, test_pred):
                err = float(abs(actual - pred))
                w.writerow([r.get("normalized_host", ""), actual, float(pred), err])
        print(f"Wrote {pred_path}", file=sys.stderr)

        # Feature importance CSV (canonical names for thesis)
        imp = results["models"][model_name].get("feature_importance", {})
        if imp:
            base = {"linear_regression": "feature_importance_linear", "random_forest_regressor": "feature_importance_rf", "gradient_boosting_regressor": "feature_importance_gb"}.get(model_name, f"feature_importance_{model_name}")
            imp_path = args.out_dir / f"{base}{file_suffix}.csv"
            with open(imp_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["feature", "importance"])
                for col in feature_columns:
                    w.writerow([col, imp.get(col, 0)])
            print(f"Wrote {imp_path}", file=sys.stderr)

    # regression_results.json
    out_json = args.out_dir / f"regression_results{file_suffix}.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {out_json}", file=sys.stderr)

    # Biggest errors CSV (worst 50 by absolute error on test set)
    by_host = {r.get("normalized_host"): r for r in test_rows}
    first_pred_path = args.out_dir / f"predictions_linear_regression{file_suffix}.csv"
    if first_pred_path.exists():
        with open(first_pred_path) as f:
            err_rows = list(csv.DictReader(f))
        err_rows.sort(key=lambda x: -float(x.get("absolute_error", 0)))
        worst = []
        for row in err_rows[:50]:
            host = row.get("normalized_host", "")
            r = {
                "normalized_host": host,
                "actual_rule_score_v2": row.get("actual_rule_score_v2", row.get("actual_rule_score")),
                "predicted_rule_score_v2": row.get("predicted_rule_score_v2", row.get("predicted_rule_score")),
                "absolute_error": row.get("absolute_error"),
            }
            orig = by_host.get(host, {})
            for c in feature_columns[:8]:
                r[c] = orig.get(c, "")
            worst.append(r)
        err_path = args.out_dir / f"regression_biggest_errors{file_suffix}.csv"
        with open(err_path, "w", newline="") as f:
            if worst:
                cols = ["normalized_host", "actual_rule_score_v2", "predicted_rule_score_v2", "absolute_error"] + feature_columns[:8]
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(worst)
        print(f"Wrote {err_path}", file=sys.stderr)

    # Plots (use stored test predictions and importance from results)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots.", file=sys.stderr)
    else:
        # Rule score distribution
        fig, ax = plt.subplots()
        ax.hist(y_test, bins=20, edgecolor="black", alpha=0.7)
        ax.set_xlabel("rule_score_v2")
        ax.set_ylabel("Count")
        ax.set_title("Test set: rule_score_v2 distribution" + (f" ({suffix})" if suffix else ""))
        fig.savefig(PLOTS_DIR / f"rule_score_distribution{file_suffix}.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Wrote {PLOTS_DIR / f'rule_score_distribution{file_suffix}.png'}", file=sys.stderr)

        for model_name in stored_preds:
            test_pred = stored_preds[model_name]
            # Actual vs predicted
            fig, ax = plt.subplots()
            ax.scatter(y_test, test_pred, alpha=0.5)
            ax.plot([0, 110], [0, 110], "r--", label="y=x")
            ax.set_xlabel("Actual rule_score_v2")
            ax.set_ylabel("Predicted rule_score_v2")
            ax.set_title(f"Actual vs predicted — {model_name}" + (f" ({suffix})" if suffix else ""))
            ax.legend()
            ax.set_xlim(0, 110)
            ax.set_ylim(0, 110)
            fig.savefig(PLOTS_DIR / f"actual_vs_predicted_{model_name}{file_suffix}.png", dpi=150, bbox_inches="tight")
            plt.close()

            # Residuals
            fig, ax = plt.subplots()
            residuals = y_test - test_pred
            ax.scatter(test_pred, residuals, alpha=0.5)
            ax.axhline(0, color="r", linestyle="--")
            ax.set_xlabel("Predicted rule_score_v2")
            ax.set_ylabel("Residual")
            ax.set_title(f"Residual plot — {model_name}" + (f" ({suffix})" if suffix else ""))
            fig.savefig(PLOTS_DIR / f"residuals_{model_name}{file_suffix}.png", dpi=150, bbox_inches="tight")
            plt.close()

            # Top 15 feature importance
            imp = results["models"][model_name].get("feature_importance", {})
            if imp:
                sorted_imp = sorted(imp.items(), key=lambda x: -abs(x[1]))[:15]
                names = [x[0] for x in sorted_imp]
                vals = [x[1] for x in sorted_imp]
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.barh(range(len(names)), vals, align="center")
                ax.set_yticks(range(len(names)))
                ax.set_yticklabels(names, fontsize=8)
                ax.set_xlabel("Importance")
                ax.set_title(f"Top 15 feature importance — {model_name}" + (f" ({suffix})" if suffix else ""))
                ax.invert_yaxis()
                fig.savefig(PLOTS_DIR / f"feature_importance_top15_{model_name}{file_suffix}.png", dpi=150, bbox_inches="tight")
                plt.close()
        print(f"Plots saved to {PLOTS_DIR}", file=sys.stderr)

    # Print summary
    print("\n--- Validation ---")
    for name, data in results["models"].items():
        v = data["val"]
        print(f"  {name}: MAE={v['mae']:.3f} RMSE={v['rmse']:.3f} R²={v['r2']:.4f}")
    print("--- Test ---")
    for name, data in results["models"].items():
        t = data["test"]
        print(f"  {name}: MAE={t['mae']:.3f} RMSE={t['rmse']:.3f} R²={t['r2']:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
