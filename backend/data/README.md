# Backend data directory

## Canonical source of truth

- **scans.v3_combined.cleaned.jsonl** — Master cleaned dataset (one row per scanned host: metadata, `features`, `evidence`, `rule_score`, `rule_grade`, `rule_label`, `rule_reasons`). This is the single source for the ML regression pipeline. Do not delete; older dataset versions are in `archive/`.

## Target lists

- **targets.txt** — List of targets for batch scanning (one per line). Blank lines and lines starting with `#` are ignored.
- **targets_extra.txt** — Additional targets for extended runs.

## Archive

- **archive/old_scans/** — Older scan outputs (v1, v2, v3 single-run, cleaned intermediates).
- **archive/old_failures/** — Failure logs from previous runs.
- **archive/old_ml_outputs/** — Previous classification datasets and baseline results (pre–regression).

Do not commit raw scan/failure files if they contain sensitive targets (see `.gitignore`).

---

## Regression ML pipeline (rule_score prediction)

We predict **rule_score** (0–100) from **raw passive security features** only. This is a regression task, not binary classification.

### Why regression (not classification)

- **Classification** (predicting `rule_label` good/risky) largely reproduced the rule engine that derived the label from the same features, which is not the thesis goal.
- **Regression** predicts the continuous score so the model can learn relationships and interactions among features rather than a threshold.

### Why leakage-safe features

We **exclude** from model inputs:

- Labels and proxies: `rule_score`, `rule_label`, `rule_grade`, `rule_reasons`, `csp_score`, `tls_version_score`
- Metadata and evidence: `scan_timestamp`, `input_target`, `requested_url`, `final_url`, `evidence`
- Legacy duplicate names (we keep one canonical name per concept)

So the model sees only raw security posture (e.g. has_https, has_csp, cookie_secure, status buckets) and derived missing-value indicators (e.g. `tls_version_missing`, `cert_days_missing`, `response_time_log`).

### Canonical files after running the pipeline

```
data/
  scans.v3_combined.cleaned.jsonl   # master input
  archive/...
  ml/
    regression_feature_schema.json
    dataset_regression_full.csv
    dataset_regression_reachable.csv
    train_regression_full.csv
    val_regression_full.csv
    test_regression_full.csv
    train_regression_reachable.csv
    val_regression_reachable.csv
    test_regression_reachable.csv
    results/
      regression_results.json
      predictions_linear_regression.csv
      predictions_random_forest_regressor.csv
      predictions_gradient_boosting_regressor.csv
      feature_importance_linear.csv
      feature_importance_rf.csv
      feature_importance_gb.csv
      regression_biggest_errors.csv
      plots/
        rule_score_distribution.png
        actual_vs_predicted_*.png
        residuals_*.png
        feature_importance_top15_*.png
```

### How to run

From the **backend** directory:

1. **Export regression datasets** (from master JSONL; creates full and reachable CSVs + schema):
   ```bash
   python3 scripts/export_regression_dataset.py
   ```

2. **Split into train/val/test** (optional: run for full and for reachable):
   ```bash
   python3 scripts/split_regression_dataset.py --input data/ml/dataset_regression_full.csv
   python3 scripts/split_regression_dataset.py --input data/ml/dataset_regression_reachable.csv
   ```

3. **Train regression baselines** (Linear Regression, Random Forest, Gradient Boosting; writes metrics, predictions, importance, plots, error analysis):
   ```bash
   python3 models/train_regression_baseline.py
   ```
   To use reachable splits:
   ```bash
   python3 models/train_regression_baseline.py --train data/ml/train_regression_reachable.csv --val data/ml/val_regression_reachable.csv --test data/ml/test_regression_reachable.csv
   ```

Reproducibility: export and split use deterministic logic; training uses fixed random seeds (e.g. 42).
