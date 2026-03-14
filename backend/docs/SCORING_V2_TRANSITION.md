# Scoring v2 transition summary

Scoring v2 is the **official label set** across the thesis pipeline. This document confirms alignment.

## 1. Frontend score

- **Source:** Scan API response fields `rule_score`, `rule_grade`, `rule_label`, `rule_reasons`.
- **Backend behavior:** These are set from **v2** (`rule_score_v2`, `rule_grade_v2`, etc.). V3 is still computed and returned as `rule_score_v3`, `rule_grade_v3`, etc. for comparison/debugging.
- **Result:** The report page displays the v2 score as the primary overall score without code changes.

## 2. Backend score

- **Live scan:** `backend/services/passive_scan.py` calls both `compute_rule_score` (v3) and `compute_rule_score_v2` (v2). The `ScanResult` primary fields are populated from v2; v3 is attached as `rule_score_v3`, `rule_grade_v3`, `rule_label_v3`, `rule_reasons_v3`.
- **Schema:** `backend/schemas.py` `ScanResult` includes `rule_score_v2`, `rule_grade_v2`, `rule_label_v2`, `rule_reasons_v2` and the v3 legacy fields.

## 3. Saved dataset labels

- **Canonical dataset:** `data/processed/scans.v3_combined.cleaned.jsonl` contains per-row:
  - `rule_score_v2`, `rule_grade_v2`, `rule_label_v2`, `rule_reasons_v2`
  - (v3 fields `rule_score`, `rule_grade`, `rule_label`, `rule_reasons` remain for reference.)
- **Enrichment:** Run `scripts/enrich_canonical_v2.py` to add v2 to an existing combined JSONL. New runs of `scripts/clean_scans_jsonl.py` compute v2 during normalization.

## 4. ML target and exports

- **Regression target:** `rule_score_v2` (0–110, category-capped, bonuses when score ≥ 85).
- **Export:** `scripts/export_regression_dataset.py` uses `rule_score_v2` as the target column and writes `data/ml/dataset_regression_full.csv` (and reachable subset).
- **Schema:** `data/ml/regression_feature_schema.json` has `"target_column": "rule_score_v2"`.
- **Splits:** `scripts/split_regression_dataset.py` stratifies by `rule_score_v2` (bins 0–22, 22–44, …).
- **Training:** `models/train_regression_baseline.py` and `scripts/train_hist_gradient_boosting.py` use `TARGET_COLUMN = "rule_score_v2"`.

## 5. Trained model and inference

- **Artifacts:** `data/ml/artifacts/hist_gradient_boosting_depth5.*` are trained to predict **rule_score_v2**.
- **Inference:** `services/ml_inference.py` loads that model; `predicted_rule_score` in the API is therefore a v2-scale prediction.

## 6. Score context (percentile / distribution)

- **Service:** `services/score_context.py` builds the distribution from `rule_score_v2` when present in the canonical JSONL (fallback to `rule_score` for older data). Percentile is computed against that distribution.

## Consistency checklist

| Layer            | Uses v2? | Notes                                      |
|------------------|----------|--------------------------------------------|
| Frontend display | Yes      | `rule_score` / `rule_grade` = v2 from API  |
| Scan API         | Yes      | Primary fields = v2; v3 in _v3 fields     |
| Canonical JSONL  | Yes      | `rule_score_v2` (and v3) persisted         |
| ML export CSV    | Yes      | Target column `rule_score_v2`              |
| Train/val/test   | Yes      | Stratify and train on `rule_score_v2`      |
| HistGradient model | Yes   | Predicts v2 scale; artifacts in data/ml/artifacts |
| Score context    | Yes      | Distribution from `rule_score_v2`           |

All layers are aligned on **scoring v2** as the official label set.
