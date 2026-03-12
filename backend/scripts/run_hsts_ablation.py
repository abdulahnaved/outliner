#!/usr/bin/env python3
"""
HSTS ablation: train same regression models with all HSTS-related features removed
at training time. Compare performance to original (with HSTS) and save results,
comparison table, GB plots, and summary.

Does not modify dataset files; only drops HSTS columns when building X.
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

# Same paths as full-dataset regression (now under ml/datasets)
TRAIN_PATH = ML_DIR / "datasets" / "train_regression_full.csv"
VAL_PATH = ML_DIR / "datasets" / "val_regression_full.csv"
TEST_PATH = ML_DIR / "datasets" / "test_regression_full.csv"

METADATA_COLUMNS = frozenset({"normalized_host"})
TARGET_COLUMN = "rule_score"

# All HSTS-related feature names to remove at training time (drop from X only).
HSTS_FEATURE_NAMES = frozenset({
    "has_hsts",
    "hsts_max_age",
    "hsts_max_age_days",
    "hsts_long",
    "hsts_include_subdomains",
    "hsts_preload",
})


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path) as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        rows = list(r)
    return rows, fieldnames


def get_feature_columns(fieldnames: list[str], exclude: frozenset[str] | None = None) -> list[str]:
    base = [c for c in fieldnames if c not in METADATA_COLUMNS and c != TARGET_COLUMN]
    if exclude:
        base = [c for c in base if c not in exclude]
    return base


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
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    for p in (TRAIN_PATH, VAL_PATH, TEST_PATH):
        if not p.exists():
            print(f"Not found: {p}", file=sys.stderr)
            return 1

    train_rows, fieldnames = load_csv(TRAIN_PATH)
    feature_columns_all = get_feature_columns(fieldnames)
    feature_columns = [c for c in feature_columns_all if c not in HSTS_FEATURE_NAMES]
    removed = [c for c in feature_columns_all if c in HSTS_FEATURE_NAMES]
    print(f"Removed HSTS features ({len(removed)}): {removed}", file=sys.stderr)
    print(f"Features used: {len(feature_columns)}", file=sys.stderr)

    val_rows, _ = load_csv(VAL_PATH)
    test_rows, _ = load_csv(TEST_PATH)

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

    def eval_metrics(y_true, y_pred):
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2": float(r2_score(y_true, y_pred)),
        }

    models_config = [
        ("linear_regression", LinearRegression(), X_train_scaled, X_val_scaled, X_test_scaled),
        ("random_forest_regressor", RandomForestRegressor(random_state=42), X_train, X_val, X_test),
        ("gradient_boosting_regressor", GradientBoostingRegressor(random_state=42), X_train, X_val, X_test),
    ]

    experiment = {
        "experiment": "regression_no_hsts",
        "description": "Same splits and models as full regression; HSTS features removed at training time.",
        "removed_features": list(HSTS_FEATURE_NAMES),
        "n_features_used": len(feature_columns),
        "feature_columns": feature_columns,
        "models": {},
    }

    gb_test_pred = None
    gb_importance = None

    for model_name, model, X_tr, X_va, X_te in models_config:
        model.fit(X_tr, y_train)
        val_pred = model.predict(X_va)
        test_pred = model.predict(X_te)
        experiment["models"][model_name] = {
            "val": eval_metrics(y_val, val_pred),
            "test": eval_metrics(y_test, test_pred),
        }
        if hasattr(model, "coef_"):
            experiment["models"][model_name]["feature_importance"] = dict(zip(feature_columns, [float(x) for x in model.coef_.ravel()]))
        elif hasattr(model, "feature_importances_"):
            experiment["models"][model_name]["feature_importance"] = dict(zip(feature_columns, [float(x) for x in model.feature_importances_]))

        if model_name == "gradient_boosting_regressor":
            gb_test_pred = test_pred
            gb_importance = experiment["models"][model_name].get("feature_importance")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # regression_no_hsts_experiment.json
    out_json = RESULTS_DIR / "regression_no_hsts_experiment.json"
    with open(out_json, "w") as f:
        json.dump(experiment, f, indent=2)
    print(f"Wrote {out_json}", file=sys.stderr)

    # regression_no_hsts_experiment.csv (model, MAE, RMSE, R2 — test set)
    out_csv = RESULTS_DIR / "regression_no_hsts_experiment.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "MAE", "RMSE", "R2"])
        for name in experiment["models"]:
            t = experiment["models"][name]["test"]
            w.writerow([name, t["mae"], t["rmse"], t["r2"]])
    print(f"Wrote {out_csv}", file=sys.stderr)

    # hsts_ablation_comparison.csv: original vs no_hsts
    orig_path = RESULTS_DIR / "regression_results.json"
    if not orig_path.exists():
        print(f"Original results not found: {orig_path}", file=sys.stderr)
    else:
        with open(orig_path) as f:
            orig = json.load(f)
        rows = []
        for name in ["linear_regression", "random_forest_regressor", "gradient_boosting_regressor"]:
            o = orig.get("models", {}).get(name, {}).get("test", {})
            n = experiment["models"].get(name, {}).get("test", {})
            o_mae, o_r2 = o.get("mae"), o.get("r2")
            n_mae, n_r2 = n.get("mae"), n.get("r2")
            rows.append({
                "model": name,
                "original_R2": o_r2,
                "no_hsts_R2": n_r2,
                "delta_R2": (n_r2 - o_r2) if n_r2 is not None and o_r2 is not None else None,
                "original_MAE": o_mae,
                "no_hsts_MAE": n_mae,
                "delta_MAE": (n_mae - o_mae) if n_mae is not None and o_mae is not None else None,
            })
        comp_path = RESULTS_DIR / "hsts_ablation_comparison.csv"
        with open(comp_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["model", "original_R2", "no_hsts_R2", "delta_R2", "original_MAE", "no_hsts_MAE", "delta_MAE"])
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {comp_path}", file=sys.stderr)

    # Plots for Gradient Boosting (no HSTS)
    if gb_test_pred is not None and gb_importance is not None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not installed; skipping plots.", file=sys.stderr)
        else:
            # Actual vs predicted
            fig, ax = plt.subplots()
            ax.scatter(y_test, gb_test_pred, alpha=0.5)
            ax.plot([0, 100], [0, 100], "r--", label="y=x")
            ax.set_xlabel("Actual rule_score")
            ax.set_ylabel("Predicted rule_score")
            ax.set_title("Gradient Boosting (no HSTS features) — Actual vs predicted")
            ax.legend()
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            fig.savefig(PLOTS_DIR / "actual_vs_predicted_gradient_boosting_no_hsts.png", dpi=150, bbox_inches="tight")
            plt.close()
            print(f"Wrote {PLOTS_DIR / 'actual_vs_predicted_gradient_boosting_no_hsts.png'}", file=sys.stderr)

            # Residuals
            fig, ax = plt.subplots()
            residuals = y_test - gb_test_pred
            ax.scatter(gb_test_pred, residuals, alpha=0.5)
            ax.axhline(0, color="r", linestyle="--")
            ax.set_xlabel("Predicted rule_score")
            ax.set_ylabel("Residual")
            ax.set_title("Gradient Boosting (no HSTS) — Residual plot")
            fig.savefig(PLOTS_DIR / "residuals_gradient_boosting_no_hsts.png", dpi=150, bbox_inches="tight")
            plt.close()
            print(f"Wrote {PLOTS_DIR / 'residuals_gradient_boosting_no_hsts.png'}", file=sys.stderr)

            # Top 15 feature importance
            sorted_imp = sorted(gb_importance.items(), key=lambda x: -abs(x[1]))[:15]
            names = [x[0] for x in sorted_imp]
            vals = [x[1] for x in sorted_imp]
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.barh(range(len(names)), vals, align="center")
            ax.set_yticks(range(len(names)))
            ax.set_yticklabels(names, fontsize=8)
            ax.set_xlabel("Importance")
            ax.set_title("Gradient Boosting (no HSTS) — Top 15 feature importance")
            ax.invert_yaxis()
            fig.savefig(PLOTS_DIR / "feature_importance_gradient_boosting_no_hsts.png", dpi=150, bbox_inches="tight")
            plt.close()
            print(f"Wrote {PLOTS_DIR / 'feature_importance_gradient_boosting_no_hsts.png'}", file=sys.stderr)

    # hsts_ablation_summary.txt
    with open(orig_path) as f:
        orig = json.load(f)
    lines = [
        "HSTS ablation experiment — summary",
        "=" * 50,
        "",
        "Setup: Same regression task (target rule_score), same full-dataset splits,",
        "same models and hyperparameters. HSTS-related features were removed only at",
        "training time (has_hsts, hsts_max_age, hsts_long, hsts_include_subdomains,",
        "hsts_preload; hsts_max_age_days if present).",
        "",
    ]
    r2_drops = []
    for name in ["linear_regression", "random_forest_regressor", "gradient_boosting_regressor"]:
        o = orig.get("models", {}).get(name, {}).get("test", {})
        n = experiment["models"].get(name, {}).get("test", {})
        o_r2, n_r2 = o.get("r2"), n.get("r2")
        if o_r2 is not None and n_r2 is not None:
            r2_drops.append((name, o_r2, n_r2, n_r2 - o_r2))
    if r2_drops:
        lines.append("1. Performance impact of removing HSTS features")
        lines.append("")
        for name, o_r2, n_r2, delta in r2_drops:
            lines.append(f"   {name}:")
            lines.append(f"      Original test R² = {o_r2:.4f}, No-HSTS test R² = {n_r2:.4f}, Δ R² = {delta:+.4f}")
        lines.append("")
        avg_drop = sum(x[3] for x in r2_drops) / len(r2_drops)
        if avg_drop < -0.01:
            lines.append("2. Conclusion: Removing HSTS features significantly reduced performance.")
            lines.append(f"   Average R² drop: {avg_drop:.4f}. HSTS features carry substantial signal")
            lines.append("   for predicting rule_score.")
        elif avg_drop > 0.01:
            lines.append("2. Conclusion: Removing HSTS features slightly improved performance.")
            lines.append("   This may indicate some redundancy or over-weighting of HSTS in the")
            lines.append("   original feature set.")
        else:
            lines.append("2. Conclusion: Removing HSTS features had a small impact (|Δ R²| < 0.01).")
            lines.append("   Other features compensate; HSTS is not dominant for prediction.")
        lines.append("")
        if gb_importance and len(gb_importance) > 0:
            top3 = sorted(gb_importance.items(), key=lambda x: -abs(x[1]))[:3]
            lines.append("3. Top 3 features in Gradient Boosting without HSTS:")
            for feat, imp in top3:
                lines.append(f"   {feat}: {imp:.4f}")
            lines.append("")
    lines.append("See regression_no_hsts_experiment.json, hsts_ablation_comparison.csv for full metrics.")

    summary_path = RESULTS_DIR / "hsts_ablation_summary.txt"
    with open(summary_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {summary_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
