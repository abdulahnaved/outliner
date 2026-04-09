#!/usr/bin/env python3
"""
Evaluate multiple regression models for predicting the deterministic baseline score.

This project currently trains ML to predict rule_score_v2 from passive scan features.
That is intentionally a "learned estimator of the baseline" rather than a ground-truth
security outcome model.

This script makes model comparison explicit and thesis-friendly:
- Linear Regression
- Random Forest Regressor
- Gradient Boosting Regressor
- HistGradientBoosting Regressor

Outputs are written to data/ml/results/model_eval_* so results are easy to inspect later.
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
    out: list[float] = []
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
    y: list[float] = []
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
    ap = argparse.ArgumentParser(description="Evaluate regression models for rule_score_v2")
    ap.add_argument("--train", type=Path, default=ML_DIR / "datasets" / "train_regression_full.csv")
    ap.add_argument("--val", type=Path, default=ML_DIR / "datasets" / "val_regression_full.csv")
    ap.add_argument("--test", type=Path, default=ML_DIR / "datasets" / "test_regression_full.csv")
    ap.add_argument("--out-dir", type=Path, default=RESULTS_DIR)
    ap.add_argument("--tag", type=str, default="full", help="Label for outputs (e.g. reachable)")
    args = ap.parse_args()

    def resolve(p: Path) -> Path:
        if p.exists():
            return p.resolve()
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
    val_rows, _ = load_csv(val_path)
    test_rows, _ = load_csv(test_path)

    if not feature_columns:
        print("No feature columns.", file=sys.stderr)
        return 1

    import numpy as np
    from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.preprocessing import StandardScaler

    X_train, y_train = build_X_y(train_rows, feature_columns)
    X_val, y_val = build_X_y(val_rows, feature_columns)
    X_test, y_test = build_X_y(test_rows, feature_columns)

    X_train = np.asarray(X_train, dtype=float)
    X_val = np.asarray(X_val, dtype=float)
    X_test = np.asarray(X_test, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    y_val = np.asarray(y_val, dtype=float)
    y_test = np.asarray(y_test, dtype=float)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "linear_regression": ("scaled", LinearRegression()),
        "random_forest_regressor": ("raw", RandomForestRegressor(random_state=42)),
        "gradient_boosting_regressor": ("raw", GradientBoostingRegressor(random_state=42)),
        "hist_gradient_boosting_regressor": (
            "raw",
            HistGradientBoostingRegressor(max_depth=5, learning_rate=0.05, max_iter=300, random_state=42),
        ),
    }

    def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        return {"mae": float(mean_absolute_error(y_true, y_pred)), "rmse": rmse, "r2": float(r2_score(y_true, y_pred))}

    tag = (args.tag or "full").strip() or "full"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "train_samples": int(len(y_train)),
        "val_samples": int(len(y_val)),
        "test_samples": int(len(y_test)),
        "n_features": int(len(feature_columns)),
        "target": TARGET_COLUMN,
        "models": {},
    }

    rows_for_csv: list[list] = [["model", "split", "MAE", "RMSE", "R2"]]

    for name, (space, model) in models.items():
        Xtr = X_train_scaled if space == "scaled" else X_train
        Xva = X_val_scaled if space == "scaled" else X_val
        Xte = X_test_scaled if space == "scaled" else X_test
        model.fit(Xtr, y_train)
        pred_val = model.predict(Xva)
        pred_test = model.predict(Xte)
        m_val = metrics(y_val, pred_val)
        m_test = metrics(y_test, pred_test)
        results["models"][name] = {"val": m_val, "test": m_test, "feature_space": space}
        rows_for_csv.append([name, "val", m_val["mae"], m_val["rmse"], m_val["r2"]])
        rows_for_csv.append([name, "test", m_test["mae"], m_test["rmse"], m_test["r2"]])

        # Save test predictions for later error inspection / plots.
        pred_path = out_dir / f"model_eval_{tag}_{ts}_predictions_{name}.csv"
        with open(pred_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["normalized_host", "actual_rule_score_v2", "predicted_rule_score_v2", "delta", "abs_error"])
            for r, actual, pred in zip(test_rows, y_test, pred_test):
                delta = float(pred - actual)
                w.writerow([r.get("normalized_host", ""), float(actual), float(pred), delta, float(abs(delta))])

    json_path = out_dir / f"model_eval_{tag}_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    csv_path = out_dir / f"model_eval_{tag}_{ts}.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows_for_csv)

    print(f"Wrote {json_path}", file=sys.stderr)
    print(f"Wrote {csv_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

