# Backend

FastAPI app: scan API, rule-based scoring, and optional ML-predicted score.

## Interactive API docs

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

## Scan status and failed targets

The scan pipeline degrades gracefully for unreachable or failing targets; the API **always returns 200** with a structured `ScanResult` (except for bad request: invalid target or SSRF, which return 400).

- **`scan_status`** — one of:
  - `"success"`: full scan completed; rule and ML scores are present when available.
  - `"failed"`: scan could not get a usable response (timeout, DNS, TLS, connection error, etc.); scores are `null`, features are defaults.
- **`scan_error_type`** / **`scan_error_message`** — set when `scan_status` is `"failed"`. Error types include: `timeout`, `dns_error`, `tls_error`, `connection_error`, `http_error`, `blocked`, `unknown`.
- **When score fields are null:** for `failed`, `rule_score`, `rule_grade`, and `rule_label` are `null`; `rule_reasons` is `[]`. No synthetic fallback scores are invented. ML prediction is not run for `failed`; `prediction_available` is `false` and `predicted_rule_score` is `null` when prediction cannot be computed.
- **Preserved fields:** even when failed, the response includes `input_target`, `normalized_host`, `requested_url`, and when available `final_url`, `final_status_code`, `timing_ms`, `response_time`, `is_blocked`.

**Smoke test for failed scans:** from `backend`, run `python scripts/test_failed_scan_response.py` to ensure an unreachable target returns a structured result with `scan_status` `"failed"` and no unhandled exception.

## ML integration (rule_score prediction)

- **Final model:** `HistGradientBoostingRegressor` (max_depth=5), trained on the full regression dataset; target is `rule_score`.
- **Runtime artifacts** are stored under `backend/data/ml/artifacts/`:
  - `hist_gradient_boosting_depth5.joblib` — trained model
  - `hist_gradient_boosting_depth5_features.json` — feature column order used at training time
  - `hist_gradient_boosting_depth5_preprocessing.json` — preprocessing metadata (expected features, missing-value handling, derived columns)
- **Inference** is done in `backend/services/ml_inference.py` via `predict_rule_score(scan_result)`. Feature building is centralized in `backend/services/ml_features.py` so training export and runtime use the same logic.
- **Scan/report responses** include both rule-based and ML fields:
  - Rule-based (unchanged): `rule_score`, `rule_grade`, `rule_label`, `rule_reasons`
  - ML (additive): `prediction_available`, `predicted_rule_score`, `ml_model_name`, `ml_model_variant`, `prediction_error` (when prediction is unavailable)
- If the model artifact is missing or prediction fails, the scan still succeeds and rule-based scoring is returned; ML fields indicate unavailability.
- **Regenerating the model artifact:** run the training script (after exporting and splitting the regression dataset), which writes the joblib and JSON files into `data/ml/artifacts/`:

  ```bash
  cd backend
  python scripts/export_regression_dataset.py
  python scripts/split_regression_dataset.py
  python scripts/train_hist_gradient_boosting.py
  ```

- **Smoke test:** from `backend`, run `python scripts/test_ml_inference.py` to verify inference returns a numeric predicted score (requires artifacts to exist).
