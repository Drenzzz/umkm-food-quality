from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image


INPUT_FIELDNAMES = [
    "image_id",
    "source_type",
    "source_batch",
    "dataset_name",
    "dataset_slug",
    "source_group",
    "product_name",
    "product_domain",
    "label_lane",
    "training_label",
    "batch_name",
    "filename",
    "relative_path",
    "source_workspace",
    "review_status",
    "notes",
]

OUTPUT_FIELDNAMES = [
    "image_id",
    "filename",
    "relative_path",
    "dataset_name",
    "dataset_slug",
    "source_type",
    "product_name",
    "product_domain",
    "final_label",
    "source_group",
    "review_status",
    "source_batch",
    "batch_name",
    "original_filename",
    "original_relative_path",
]

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare manual image batches for training workspace.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path for umkm-food-quality.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=None,
        help="Input CSV path for normalized manual training labels.",
    )
    parser.add_argument(
        "--output-metadata",
        type=Path,
        default=None,
        help="Output CSV path for prepared manual training metadata.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=224,
        help="Final square image size.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    input_csv = args.input_csv.resolve() if args.input_csv else project_root / "dataset" / "metadata" / "manual_training_labels.csv"
    output_metadata = args.output_metadata.resolve() if args.output_metadata else project_root / "dataset" / "metadata" / "manual_prepared_metadata.csv"
    report_path = args.report_path.resolve() if args.report_path else project_root / "dataset" / "metadata" / "manual_prepare_report.json"

    rows = read_rows(input_csv)
    prepared_rows, report = prepare_rows(project_root, rows, args.image_size)
    write_csv(output_metadata, prepared_rows)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Input rows scanned: {len(rows)}")
    print(f"Prepared rows written: {len(prepared_rows)}")
    print(f"Skipped rows: {report['skipped_count']}")
    print(f"Output CSV: {output_metadata}")
    print(f"Report JSON: {report_path}")
    return 0


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
    if not rows:
        return []

    missing = [field for field in INPUT_FIELDNAMES if field not in rows[0]]
    if missing:
        raise ValueError(f"Input CSV is missing required fields: {', '.join(missing)}")
    return rows


def prepare_rows(project_root: Path, rows: list[dict[str, str]], image_size: int) -> tuple[list[dict[str, str]], dict[str, object]]:
    workspace_root = project_root / "dataset" / "working" / "manual_normalized"
    archive_root = project_root / "dataset" / "archive" / "rejected"

    prepared_rows: list[dict[str, str]] = []
    summary_by_product = defaultdict(lambda: Counter())
    errors: list[dict[str, str]] = []
    skipped_count = 0

    for row in rows:
        original_relative_path = row["relative_path"]
        source_path = project_root.parents[0] / original_relative_path
        final_label = row["training_label"]
        product_name = row["product_name"]

        try:
            normalized_filename = build_output_filename(row)
            destination_path = workspace_root / product_name / final_label / normalized_filename
            transform_image(source_path, destination_path, image_size)

            prepared_rows.append(
                {
                    "image_id": row["image_id"],
                    "filename": normalized_filename,
                    "relative_path": str(destination_path.relative_to(project_root)).replace("\\", "/"),
                    "dataset_name": row["dataset_name"],
                    "dataset_slug": row["dataset_slug"],
                    "source_type": row["source_type"],
                    "product_name": product_name,
                    "product_domain": row["product_domain"],
                    "final_label": final_label,
                    "source_group": row["source_group"],
                    "review_status": "prepared",
                    "source_batch": row["source_batch"],
                    "batch_name": row["batch_name"],
                    "original_filename": row["filename"],
                    "original_relative_path": original_relative_path,
                }
            )
            summary_by_product[product_name][final_label] += 1
        except Exception as error:
            skipped_count += 1
            archive_root.mkdir(parents=True, exist_ok=True)
            marker_path = archive_root / f"{row['image_id']}.txt"
            marker_path.write_text(str(source_path), encoding="utf-8")
            errors.append(
                {
                    "image_id": row["image_id"],
                    "source_path": str(source_path),
                    "error": str(error),
                }
            )

    report = {
        "prepared_count": len(prepared_rows),
        "skipped_count": skipped_count,
        "summary_by_product": {name: dict(counter) for name, counter in summary_by_product.items()},
        "errors": errors,
    }
    return prepared_rows, report


def build_output_filename(row: dict[str, str]) -> str:
    stable_source = f"{row['image_id']}:{row['product_name']}:{row['training_label']}:{row['filename']}"
    digest = hashlib.sha1(stable_source.encode("utf-8")).hexdigest()[:12]
    return f"manual_{digest}.jpg"


def transform_image(source_path: Path, destination_path: Path, image_size: int) -> None:
    if source_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"Unsupported image suffix: {source_path.suffix}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        image.verify()

    with Image.open(source_path) as image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        image = image.resize((image_size, image_size), resample=Image.Resampling.LANCZOS)
        image.save(destination_path, "JPEG", optimize=True, quality=90)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
