"""
Runtime ML inference for rule_score prediction.

Loads the saved HistGradientBoostingRegressor artifact and applies the same
feature preprocessing as training. Used by the scan pipeline to add
predicted_rule_score to scan responses.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ml_features import build_feature_row, feature_row_to_vector

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ARTIFACTS_DIR = _BACKEND_DIR / "data" / "ml" / "artifacts"
_MODEL_STEM = "hist_gradient_boosting_depth5"
_ML_MODEL_NAME = "HistGradientBoostingRegressor"
_ML_MODEL_VARIANT = "full_dataset_depth5"


def _load_artifacts() -> tuple[Any, list[str], dict]:
    """Load model, feature columns, and preprocessing metadata. Raises on missing/corrupt."""
    model_path = _ARTIFACTS_DIR / f"{_MODEL_STEM}.joblib"
    features_path = _ARTIFACTS_DIR / f"{_MODEL_STEM}_features.json"
    preprocess_path = _ARTIFACTS_DIR / f"{_MODEL_STEM}_preprocessing.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"Feature order not found: {features_path}")

    import joblib
    model = joblib.load(model_path)
    with open(features_path) as f:
        feature_columns = json.load(f)
    preprocessing = {}
    if preprocess_path.exists():
        with open(preprocess_path) as f:
            preprocessing = json.load(f)
    return model, feature_columns, preprocessing


def predict_rule_score(scan_result: dict[str, Any]) -> dict[str, Any]:
    """
    Run ML prediction for rule_score from one scan result.

    Input: scan result dict with top-level and nested "features" (same shape as pipeline output).
    Output: dict with prediction_available, predicted_rule_score, ml_model_name, ml_model_variant,
            and optionally prediction_error when prediction is unavailable.
    """
    out: dict[str, Any] = {
        "prediction_available": False,
        "predicted_rule_score": None,
        "ml_model_name": _ML_MODEL_NAME,
        "ml_model_variant": _ML_MODEL_VARIANT,
    }
    try:
        model, feature_columns, _ = _load_artifacts()
    except Exception as e:
        out["prediction_error"] = str(e)
        return out

    try:
        flat = build_feature_row(scan_result)
        vec = feature_row_to_vector(flat, feature_columns)
        import numpy as np
        X = np.asarray([vec], dtype=float)
        pred = model.predict(X)
        score = float(pred[0])
        out["prediction_available"] = True
        out["predicted_rule_score"] = round(score, 2)
    except Exception as e:
        out["prediction_error"] = str(e)
    return out
