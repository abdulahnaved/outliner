#!/usr/bin/env python3
"""
Baseline classifiers for rule_label prediction.

Loads stratified train/val/test CSVs from data/ml/, trains Logistic Regression
and Random Forest with class_weight='balanced' (LR), evaluates on val and test
with accuracy, precision, recall, F1, ROC-AUC, confusion matrix. Saves metrics
and feature importance (LR coefficients, RF importances) to data/ml/results/.

Assumptions:
  - CSV has normalized_host (metadata), rule_score and rule_label (targets), rest are features.
  - All feature columns are numeric (including binary 0/1).
  - Missing/empty cells are handled by filling with 0.
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

# Column roles: excluded from feature matrix.
METADATA_COLUMNS = frozenset({"normalized_host"})
TARGET_COLUMNS = frozenset({"rule_label", "rule_score"})


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path) as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        rows = list(r)
    return rows, fieldnames


def get_feature_columns(fieldnames: list[str]) -> list[str]:
    """Feature columns = all except metadata and targets."""
    return [
        c for c in fieldnames
        if c not in METADATA_COLUMNS and c not in TARGET_COLUMNS
    ]


def row_to_numeric(row: dict, feature_columns: list[str]) -> list[float]:
    """Convert one row to a list of floats for feature columns; empty/missing -> 0."""
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


def build_X_y(rows: list[dict], feature_columns: list[str]) -> tuple[list[list[float]], list[int]]:
    X = [row_to_numeric(r, feature_columns) for r in rows]
    y = []
    for r in rows:
        v = r.get("rule_label")
        if v is None or v == "":
            y.append(0)
            continue
        try:
            y.append(int(float(v)))
        except (ValueError, TypeError):
            y.append(0)
    return X, y


def main() -> int:
    ap = argparse.ArgumentParser(description="Train baseline LR and RF on rule_label")
    ap.add_argument("--train", type=Path, default=ML_DIR / "train_full.csv", help="Train CSV")
    ap.add_argument("--val", type=Path, default=ML_DIR / "val_full.csv", help="Validation CSV")
    ap.add_argument("--test", type=Path, default=ML_DIR / "test_full.csv", help="Test CSV")
    ap.add_argument("--out-dir", type=Path, default=RESULTS_DIR, help="Results output directory")
    ap.add_argument("--prefix", type=str, default="baseline", help="Prefix for result filenames")
    args = ap.parse_args()

    # Resolve paths under ML_DIR if relative/missing
    def resolve(p: Path) -> Path:
        if p.exists():
            return p.resolve()
        alt = ML_DIR / p.name
        return alt.resolve() if alt.exists() else p.resolve()

    train_path = resolve(args.train)
    val_path = resolve(args.val)
    test_path = resolve(args.test)

    if not train_path.exists():
        print(f"Train file not found: {train_path}", file=sys.stderr)
        return 1
    if not val_path.exists():
        print(f"Val file not found: {val_path}", file=sys.stderr)
        return 1
    if not test_path.exists():
        print(f"Test file not found: {test_path}", file=sys.stderr)
        return 1

    train_rows, fieldnames = load_csv(train_path)
    feature_columns = get_feature_columns(fieldnames)
    if not feature_columns:
        print("No feature columns found.", file=sys.stderr)
        return 1

    val_rows, _ = load_csv(val_path)
    test_rows, _ = load_csv(test_path)

    X_train, y_train = build_X_y(train_rows, feature_columns)
    X_val, y_val = build_X_y(val_rows, feature_columns)
    X_test, y_test = build_X_y(test_rows, feature_columns)

    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import (
            accuracy_score,
            precision_score,
            recall_score,
            f1_score,
            roc_auc_score,
            confusion_matrix,
        )
    except ImportError as e:
        print(f"Required packages missing: {e}. Install numpy and scikit-learn.", file=sys.stderr)
        return 1

    X_train = np.asarray(X_train)
    X_val = np.asarray(X_val)
    X_test = np.asarray(X_test)
    y_train = np.asarray(y_train)
    y_val = np.asarray(y_val)
    y_test = np.asarray(y_test)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train_samples": len(y_train),
        "val_samples": len(y_val),
        "test_samples": len(y_test),
        "n_features": len(feature_columns),
        "feature_columns": feature_columns,
        "models": {},
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(y_true, y_pred, y_prob=None):
        out = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        }
        if y_prob is not None and len(np.unique(y_true)) > 1:
            try:
                out["roc_auc"] = float(roc_auc_score(y_true, y_prob))
            except ValueError:
                out["roc_auc"] = None
        else:
            out["roc_auc"] = None
        return out

    # --- Logistic Regression (scaled, balanced) ---
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    lr = LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000)
    lr.fit(X_train_scaled, y_train)

    lr_val_pred = lr.predict(X_val_scaled)
    proba_val = lr.predict_proba(X_val_scaled)
    pos_idx = int(np.argmax(lr.classes_ == 1))
    lr_val_prob = proba_val[:, pos_idx]
    lr_test_pred = lr.predict(X_test_scaled)
    proba_test = lr.predict_proba(X_test_scaled)
    lr_test_prob = proba_test[:, pos_idx]

    results["models"]["logistic_regression"] = {
        "val": evaluate(y_val, lr_val_pred, lr_val_prob),
        "test": evaluate(y_test, lr_test_pred, lr_test_prob),
        "feature_importance": dict(zip(feature_columns, [float(x) for x in lr.coef_.ravel()])),
    }

    # --- Random Forest (no scaling, balanced) ---
    rf = RandomForestClassifier(class_weight="balanced", random_state=42)
    rf.fit(X_train, y_train)

    rf_val_pred = rf.predict(X_val)
    proba_val_rf = rf.predict_proba(X_val)
    pos_idx_rf = int(np.argmax(rf.classes_ == 1))
    rf_val_prob = proba_val_rf[:, pos_idx_rf]
    rf_test_pred = rf.predict(X_test)
    proba_test_rf = rf.predict_proba(X_test)
    rf_test_prob = proba_test_rf[:, pos_idx_rf]

    results["models"]["random_forest"] = {
        "val": evaluate(y_val, rf_val_pred, rf_val_prob),
        "test": evaluate(y_test, rf_test_pred, rf_test_prob),
        "feature_importance": dict(zip(feature_columns, [float(x) for x in rf.feature_importances_])),
    }

    # Save JSON report
    out_path = args.out_dir / f"{args.prefix}_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {out_path}", file=sys.stderr)

    # Save feature importance CSVs for thesis/reports
    for name, key in [("logistic_regression", "logistic_regression"), ("random_forest", "random_forest")]:
        imp = results["models"][key]["feature_importance"]
        csv_path = args.out_dir / f"{args.prefix}_{name}_importance.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["feature", "importance"])
            for feat in feature_columns:
                w.writerow([feat, imp.get(feat, 0)])
        print(f"Importance saved to {csv_path}", file=sys.stderr)

    # Print summary to stdout
    print("\n--- Validation ---")
    for model_name, data in results["models"].items():
        v = data["val"]
        print(f"  {model_name}: acc={v['accuracy']:.4f} prec={v['precision']:.4f} rec={v['recall']:.4f} f1={v['f1']:.4f} auc={v.get('roc_auc')}")
    print("--- Test ---")
    for model_name, data in results["models"].items():
        t = data["test"]
        print(f"  {model_name}: acc={t['accuracy']:.4f} prec={t['precision']:.4f} rec={t['recall']:.4f} f1={t['f1']:.4f} auc={t.get('roc_auc')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
