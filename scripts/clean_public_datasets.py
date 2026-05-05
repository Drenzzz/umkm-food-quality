from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.preprocess import (
    DatasetItem,
    build_output_filename,
    classify_item_error,
    iter_public_dataset_items,
    transform_image,
    validate_image,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize public datasets into working directories.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "dataset",
        help="Source dataset root outside the project.",
    )
    parser.add_argument(
        "--mapping-csv",
        type=Path,
        default=None,
        help="Path to public dataset mapping CSV.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=224,
        help="Final square image size.",
    )
    parser.add_argument(
        "--limit-per-label",
        type=int,
        default=None,
        help="Optional cap per dataset and final label for smoke tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without writing files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    source_root = args.source_root.resolve()
    mapping_csv = args.mapping_csv.resolve() if args.mapping_csv else project_root / "dataset" / "metadata" / "public_dataset_mapping.csv"

    items = iter_public_dataset_items(source_root, mapping_csv)
    selected_items = apply_limit(items, args.limit_per_label)
    result = process_items(project_root, selected_items, args.image_size, args.dry_run)

    report_path = project_root / "dataset" / "metadata" / "public_preprocessing_report.json"
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Mode: {'dry-run' if args.dry_run else 'write'}")
    print(f"Items discovered: {len(items)}")
    print(f"Items selected: {len(selected_items)}")
    print(f"Items processed: {result['processed_count']}")
    print(f"Items skipped: {result['skipped_count']}")
    print(f"Errors captured: {len(result['errors'])}")
    print(f"Report written: {report_path}")
    return 0


def apply_limit(items: list[DatasetItem], limit_per_label: int | None) -> list[DatasetItem]:
    if limit_per_label is None:
        return items

    selected: list[DatasetItem] = []
    counters: Counter[tuple[str, str]] = Counter()
    for item in items:
        key = (item.dataset_slug, item.final_label)
        if counters[key] >= limit_per_label:
            continue
        counters[key] += 1
        selected.append(item)
    return selected


def process_items(project_root: Path, items: list[DatasetItem], image_size: int, dry_run: bool) -> dict[str, object]:
    normalized_root = project_root / "dataset" / "working" / "normalized"
    merged_root = project_root / "dataset" / "working" / "merged_public"
    archive_root = project_root / "dataset" / "archive"

    summary_by_dataset = defaultdict(lambda: Counter())
    errors: list[dict[str, str]] = []
    processed_count = 0
    skipped_count = 0

    for item in items:
        filename = build_output_filename(item)
        normalized_path = normalized_root / item.dataset_slug / item.final_label / filename
        merged_path = merged_root / item.final_label / filename

        try:
            validate_image(item.source_path)

            if dry_run:
                processed_count += 1
                summary_by_dataset[item.dataset_slug][item.final_label] += 1
                continue

            transform_image(item.source_path, normalized_path, image_size)
            transform_image(item.source_path, merged_path, image_size)
            processed_count += 1
            summary_by_dataset[item.dataset_slug][item.final_label] += 1
        except Exception as error:
            skipped_count += 1
            archive_label = classify_item_error(item, error)
            archive_marker = archive_root / archive_label / f"{filename}.txt"
            archive_marker.write_text(str(item.source_path), encoding="utf-8")
            errors.append(
                {
                    "dataset": item.dataset_name,
                    "source_path": str(item.source_path),
                    "archive_label": archive_label,
                    "error": str(error),
                }
            )

    return {
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "summary_by_dataset": {name: dict(counter) for name, counter in summary_by_dataset.items()},
        "errors": errors,
    }


if __name__ == "__main__":
    raise SystemExit(main())
