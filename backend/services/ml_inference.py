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

_RELIABILITY_STEM = f"{_MODEL_STEM}_reliability"


def _load_artifacts() -> tuple[Any, list[str], dict, Any | None, dict | None]:
    """
    Load model, feature columns, preprocessing metadata, and optional reliability artifacts.

    Reliability artifacts are additive: missing files should not break prediction.
    """
    model_path = _ARTIFACTS_DIR / f"{_MODEL_STEM}.joblib"
    features_path = _ARTIFACTS_DIR / f"{_MODEL_STEM}_features.json"
    preprocess_path = _ARTIFACTS_DIR / f"{_MODEL_STEM}_preprocessing.json"
    reliability_path = _ARTIFACTS_DIR / f"{_RELIABILITY_STEM}.joblib"
    reliability_meta_path = _ARTIFACTS_DIR / f"{_RELIABILITY_STEM}.json"
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
    reliability = None
    reliability_meta = None
    if reliability_path.exists():
        try:
            reliability = joblib.load(reliability_path)
        except Exception:
            reliability = None
    if reliability_meta_path.exists():
        try:
            with open(reliability_meta_path) as f:
                reliability_meta = json.load(f)
        except Exception:
            reliability_meta = None
    return model, feature_columns, preprocessing, reliability, reliability_meta


def _reliability_from_distance(
    reliability: Any | None,
    reliability_meta: dict | None,
    vec: list[float],
) -> tuple[str | None, str | None]:
    """
    Conservative reliability label derived from distance to training data.

    Returns (label, reason), where label is one of: higher, moderate, lower.
    If artifacts are missing, returns (None, None).
    """
    if reliability is None or not isinstance(reliability_meta, dict):
        return None, None
    try:
        scaler = reliability.get("scaler")
        nn = reliability.get("nn")
        if scaler is None or nn is None:
            return None, None
        import numpy as np
        X = np.asarray([vec], dtype=float)
        Xs = scaler.transform(X)
        k = int(reliability_meta.get("k_neighbors") or 25)
        dists, _ = nn.kneighbors(Xs, n_neighbors=k, return_distance=True)
        mean_dist = float(np.mean(dists[0])) if dists is not None else None
        q50 = float(reliability_meta.get("mean_distance_q50", 0.0))
        q80 = float(reliability_meta.get("mean_distance_q80", 0.0))
        if mean_dist is None:
            return None, None

        if mean_dist <= q50:
            label = "higher"
            reason = (
                "Feature pattern is close to many training examples (low distance). "
                "Treat as a reasonable first read; validate against the baseline and evidence."
            )
        elif mean_dist <= q80:
            label = "moderate"
            reason = (
                "Feature pattern is somewhat typical but not near the dense center of training data. "
                "Use compare mode and evidence to interpret differences vs. rules."
            )
        else:
            label = "lower"
            reason = (
                "Feature pattern is farther from training examples (higher distance). "
                "Use the learned score directionally and weigh it against deterministic rules and raw evidence."
            )
        # Add a compact numeric hint for internal debugging without overclaiming certainty.
        reason = f"{reason} (avg neighbor distance: {mean_dist:.3f})"
        return label, reason
    except Exception:
        return None, None


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
        "prediction_reliability": None,
        "prediction_reliability_reason": None,
    }
    try:
        model, feature_columns, _, reliability, reliability_meta = _load_artifacts()
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
        label, reason = _reliability_from_distance(reliability, reliability_meta, vec)
        out["prediction_reliability"] = label
        out["prediction_reliability_reason"] = reason
    except Exception as e:
        out["prediction_error"] = str(e)
    return out
