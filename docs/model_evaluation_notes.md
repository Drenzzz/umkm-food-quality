# Model Evaluation Notes

This document records the manual evaluation flow for registered model artifacts.

## Output Evaluation Script

Use the script below to inspect raw model outputs across registered artifacts:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py --split test --limit 10
```

Evaluate one specific model:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py --model-id exp_001_industry_biscuit_only --split test --limit 10
```

Write JSON output to a file:

```bash
.venv-ml/bin/python scripts/evaluate_model_outputs.py --split test --limit 10 --output /tmp/model_outputs.json
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
