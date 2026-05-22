from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit dataset metadata quality for model training readiness.")
    parser.add_argument("--master-metadata", default="dataset/metadata/master_metadata.csv", help="Master metadata CSV path.")
    parser.add_argument("--split-metadata", default="dataset/metadata/split_metadata.csv", help="Split metadata CSV path.")
    parser.add_argument("--output", default="ml/reports/dataset_quality_report.json", help="JSON output path.")
    return parser.parse_args()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    resolved = path if path.is_absolute() else PROJECT_ROOT / path
    with resolved.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counter = Counter(normalize_value(row.get(key, "")) for row in rows)
    return dict(sorted(counter.items()))


def count_nested(rows: list[dict[str, str]], first_key: str, second_key: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        grouped[normalize_value(row.get(first_key, ""))][normalize_value(row.get(second_key, ""))] += 1
    return {key: dict(sorted(counter.items())) for key, counter in sorted(grouped.items())}


def normalize_value(value: str) -> str:
    stripped = value.strip()
    return stripped or "<missing>"


def find_missing_files(rows: list[dict[str, str]]) -> list[str]:
    missing: list[str] = []
    for row in rows:
        relative_path = row.get("relative_path", "").strip()
        if not relative_path:
            continue
        if not (PROJECT_ROOT / relative_path).exists():
            missing.append(relative_path)
    return sorted(missing)


def find_duplicates(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counter = Counter(row.get(key, "").strip() for row in rows if row.get(key, "").strip())
    return dict(sorted((value, count) for value, count in counter.items() if count > 1))


def build_findings(
    split_rows: list[dict[str, str]],
    missing_files: list[str],
    duplicate_paths: dict[str, int],
    pending_review_count: int,
    missing_split_in_master_count: int,
) -> list[str]:
    findings: list[str] = []
    label_counts = Counter(normalize_value(row.get("final_label", "")) for row in split_rows)
    if len(label_counts) >= 2:
      max_count = max(label_counts.values())
      min_count = min(label_counts.values())
      if min_count and max_count / min_count >= 2:
          findings.append("label_distribution_is_imbalanced")

    split_counts = Counter(normalize_value(row.get("split", "")) for row in split_rows)
    if "<missing>" in split_counts:
        findings.append("split_metadata_contains_missing_split_values")

    if missing_files:
        findings.append("metadata_references_missing_files")

    if duplicate_paths:
        findings.append("duplicate_relative_paths_detected")

    if pending_review_count > 0:
        findings.append("pending_review_rows_present")

    if missing_split_in_master_count > 0:
        findings.append("master_metadata_contains_rows_without_split_assignment")

    return findings


def build_report(master_rows: list[dict[str, str]], split_rows: list[dict[str, str]]) -> dict[str, Any]:
    missing_files = find_missing_files(split_rows)
    duplicate_paths = find_duplicates(split_rows, "relative_path")
    duplicate_image_ids = find_duplicates(master_rows, "image_id")
    pending_review_rows = [row for row in master_rows if normalize_value(row.get("review_status", "")) == "pending_review"]
    split_image_ids = {row.get("image_id", "").strip() for row in split_rows}
    missing_split_in_master = [
        row.get("image_id", "")
        for row in master_rows
        if not row.get("split", "").strip() and row.get("image_id", "").strip() not in split_image_ids
    ]
    findings = build_findings(
        split_rows,
        missing_files,
        duplicate_paths,
        len(pending_review_rows),
        len(missing_split_in_master),
    )

    return {
        "master_metadata_rows": len(master_rows),
        "split_metadata_rows": len(split_rows),
        "master_review_status_counts": count_by(master_rows, "review_status"),
        "master_source_type_counts": count_by(master_rows, "source_type"),
        "split_label_counts": count_by(split_rows, "final_label"),
        "split_counts": count_by(split_rows, "split"),
        "product_domain_counts": count_by(split_rows, "product_domain"),
        "dataset_slug_counts": count_by(split_rows, "dataset_slug"),
        "label_by_split": count_nested(split_rows, "split", "final_label"),
        "domain_by_label": count_nested(split_rows, "product_domain", "final_label"),
        "missing_file_count": len(missing_files),
        "missing_files_preview": missing_files[:20],
        "duplicate_relative_path_count": len(duplicate_paths),
        "duplicate_relative_paths_preview": dict(list(duplicate_paths.items())[:20]),
        "duplicate_image_id_count": len(duplicate_image_ids),
        "duplicate_image_ids_preview": dict(list(duplicate_image_ids.items())[:20]),
        "pending_review_count": len(pending_review_rows),
        "pending_review_preview": [row.get("image_id", "") for row in pending_review_rows[:20]],
        "master_rows_missing_split_count": len(missing_split_in_master),
        "master_rows_missing_split_preview": missing_split_in_master[:20],
        "findings": findings,
    }


def main() -> None:
    args = parse_args()
    master_rows = load_csv_rows(Path(args.master_metadata))
    split_rows = load_csv_rows(Path(args.split_metadata))
    report = build_report(master_rows, split_rows)
    output_path = Path(args.output) if Path(args.output).is_absolute() else PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
