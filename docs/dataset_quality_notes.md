# Dataset Quality Notes

This document records the dataset quality audit flow used before retraining.

## Audit Script

Run the dataset metadata audit:

```bash
.venv-ml/bin/python scripts/audit_dataset_quality.py
```

Write the report to a custom path:

```bash
.venv-ml/bin/python scripts/audit_dataset_quality.py --output /tmp/dataset_quality_report.json
```

## Audit Coverage

The audit report currently checks:

- row counts in master and split metadata
- label distribution
- split distribution
- product domain distribution
- dataset slug distribution
- label distribution per split
- label distribution per product domain
- missing referenced files
- duplicate relative paths
- duplicate image ids
- pending review rows
- master rows with missing split values

## Output

The default report path is:

```text
ml/reports/dataset_quality_report.json
```

The report is read-only and does not modify dataset files or metadata rows.
