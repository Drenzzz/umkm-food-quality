# Model Evaluation Notes

This document records the manual evaluation flow for registered model artifacts.

## Output Evaluation Script

Use the script below to inspect raw model outputs across registered artifacts:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py --split test --limit 10
```

Evaluate one specific model:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py --model-id exp_005_combined_public_baseline --split test --limit 10
```

Write JSON output to a file:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py --split test --limit 10 --output /tmp/model_outputs.json
```

Write model collapse quality report:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py \
  --split test \
  --limit 500 \
  --output /tmp/model_outputs_500.json \
  --quality-report ml/model/model_quality_report.json
```

Write domain bias report for the active global baseline:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py \
  --model-id exp_005_combined_public_baseline \
  --split test \
  --limit 500 \
  --domain-bias-report ml/reports/domain_bias_report.json
```

## Output Fields

Each output item includes:

- `model_id`
- `image_id`
- `image_path`
- `expected_label`
- `predicted_label`
- `raw_score`
- `threshold`
- `confidence_score`
- `split`
- `dataset_slug`

## Purpose

The script is designed to reveal whether models produce varied raw scores across different images or collapse into a single class. It does not modify datasets, model artifacts, or database rows.

## Quality Gate

The quality report marks a model as failed when any of these conditions are true:

- `raw_score_unique_count <= 1`
- `dominant_prediction_share >= 0.95`
- any expected label has zero recall

The current report is stored at:

```text
ml/model/model_quality_report.json
```

## Domain Bias Report

The domain bias report stores prediction counts and recall per label for each product domain.

Default path:

```text
ml/reports/domain_bias_report.json
```

## K-Fold Cross-Validation

For more statistically robust metrics, run stratified 5-fold cross-validation:

```bash
python -m ml.cross_validate --project-root . --folds 5
```

This trains 5 separate models and reports mean ± std across folds. Results are saved to `ml/reports/kfold_cv_report.json`.

Requires GPU for practical training times (~minutes per fold on RTX 4050).

## Test-Time Augmentation (TTA)

TTA averages predictions over the original image and a horizontally flipped variant. Typically improves accuracy by 1-2% with zero retraining cost.

```bash
python -m ml.evaluate --experiment umkm_food_quality_v1 --tta
```
