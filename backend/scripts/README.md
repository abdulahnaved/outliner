# Backend scripts

Operational and research scripts for the scanner and ML pipeline. The running API lives in `backend/main.py`; these are **CLI utilities**.

| Scripts | Role |
|--------|------|
| **`batch_scan.py`** | POST `/api/scan` for each line in `data/targets.txt` (rate-limited). |
| **`test_lab.py`**, **`test_failed_scan_response.py`**, **`check_redirect_probe.py`** | Debugging / lab targets. |
| **`validate_scoring_v2.py`**, **`run_scoring_v2_dataset.py`**, **`enrich_canonical_v2.py`** | Scoring v2 dataset and checks. |
| **`export_regression_dataset.py`**, **`split_regression_dataset.py`**, **`export_ml_dataset.py`**, **`split_ml_dataset.py`** | Build ML datasets from JSONL. |
| **`train_hist_gradient_boosting.py`**, **`evaluate_regression_models.py`**, **`compute_permutation_importance.py`** | Model training / evaluation. |
| **`combine_scans.py`**, **`clean_scans_jsonl.py`**, **`summarize_dataset.py`**, **`compare_full_vs_reachable.py`** | Dataset hygiene and summaries. |
| **`export_rule_vs_ml_disagreement.py`**, **`run_hsts_ablation.py`**, **`compare_with_mozilla.py`** | Analysis / comparisons. |

For ML pipeline details, see `backend/data/README.md` and `backend/docs/`.
