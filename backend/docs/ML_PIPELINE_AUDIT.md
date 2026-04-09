# ML pipeline audit (internal note)

## What the model predicts today

The current runtime ML output (`predicted_rule_score`) is trained to predict **`rule_score_v2`** from passive scan features.

This means the ML system is (by design) learning a **smooth estimator of the deterministic baseline** rather than predicting a ground-truth security outcome.

## Why ML feels “too close” to rules

Because the **target is the rule engine score**, the model is incentivized to imitate the rule engine:

- The best possible learner will converge toward the scoring function given enough capacity and training coverage.
- Any “scientific meaning” is bounded by the validity of the heuristic target.
- Predictions will often look close to rule scores, especially on common/typical configurations.

This is not inherently wrong for a thesis demo, but it should be framed as:

- **Rule engine**: interpretable, deterministic baseline.
- **Learned model**: data-driven estimator of the baseline that can capture feature interactions and smooth discontinuities.

## Weaknesses / risks

- **Target leakage risk**: any engineered features that directly encode scoring (e.g. `csp_score`, `tls_version_score`) make ML trivially replicate rules. The regression export flow excludes these proxies; keep this constraint.
- **Reliability/confidence**: confidence derived from score percentile is not defensible. Percentile is about dataset position, not predictive certainty.
- **Distribution shift**: the model will generalize poorly for rare/edge configurations (or if the scanning feature distribution shifts over time).

## Improvements implemented in this pass

- **Multi-model evaluation**: added a script to compare multiple regressors with MAE/RMSE/R² and saved outputs.
- **Reliability signal**: runtime now exposes a conservative reliability label derived from **distance-to-training** (StandardScaler + NearestNeighbors + training quantiles), with careful language.
- **Disagreement export**: added an output flow to export rule vs ML deltas across dataset rows for thesis analysis.

## Next methodological step (optional, thesis upgrade)

If you want ML to feel less like “rule imitation,” the target must change. Options:

- supervised outcome proxy (e.g. external benchmark, vulnerability findings, or human-labeled posture classes)
- multi-task prediction (predict individual category subscores + calibrate)
- anomaly/outlier detection on feature space (unsupervised “unusual configuration” score)

Those require new labels/datasets and are out of scope for additive backend hardening.

