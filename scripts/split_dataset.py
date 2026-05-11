from __future__ import annotations

import argparse
import csv
import shutil
from collections import defaultdict
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split public metadata into train, val, and test sets.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=None,
        help="Input metadata CSV path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output split metadata CSV path.",
    )
    parser.add_argument(
        "--final-root",
        type=Path,
        default=None,
        help="Final dataset directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview split assignment without copying files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    input_csv = args.input_csv.resolve() if args.input_csv else project_root / "dataset" / "metadata" / "public_metadata.csv"
    output_csv = args.output_csv.resolve() if args.output_csv else project_root / "dataset" / "metadata" / "split_metadata.csv"
    final_root = args.final_root.resolve() if args.final_root else project_root / "dataset" / "final"

    rows = read_rows(input_csv)
    assigned_rows = assign_splits(rows)

    if not args.dry_run:
        reset_final_root(final_root)
        materialize_final_dataset(project_root, final_root, assigned_rows)

    write_rows(output_csv, assigned_rows)

    summary = summarize_splits(assigned_rows)
    print(f"Rows assigned: {len(assigned_rows)}")
    for split_name in ["train", "val", "test"]:
        print(f"{split_name}: {summary.get(split_name, 0)}")
    print(f"Output CSV: {output_csv}")
    if not args.dry_run:
        print(f"Final root: {final_root}")
    return 0


def read_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def assign_splits(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["dataset_slug"], row["final_label"])
        grouped[key].append(row)

    assigned_rows: list[dict[str, str]] = []
    for key in sorted(grouped):
        bucket = sorted(grouped[key], key=lambda row: row["image_id"])
        split_names = build_bucket_splits(len(bucket))
        for row, split_name in zip(bucket, split_names):
            updated = dict(row)
            updated["split"] = split_name
            assigned_rows.append(updated)
    return sorted(assigned_rows, key=lambda row: row["image_id"])


def build_bucket_splits(bucket_size: int) -> list[str]:
    if bucket_size <= 0:
        return []
    if bucket_size == 1:
        return ["train"]
    if bucket_size == 2:
        return ["train", "test"]
    if bucket_size == 3:
        return ["train", "val", "test"]

    train_count = max(1, round(bucket_size * 0.7))
    val_count = max(1, round(bucket_size * 0.15))
    test_count = bucket_size - train_count - val_count

    if test_count <= 0:
        test_count = 1
        train_count = max(1, train_count - 1)

    while train_count + val_count + test_count > bucket_size:
        if train_count >= val_count and train_count > 1:
            train_count -= 1
        elif val_count > 1:
            val_count -= 1
        else:
            test_count -= 1

    while train_count + val_count + test_count < bucket_size:
        train_count += 1

    return (["train"] * train_count) + (["val"] * val_count) + (["test"] * test_count)


def reset_final_root(final_root: Path) -> None:
    if final_root.exists():
        shutil.rmtree(final_root)
    for split_name in ["train", "val", "test"]:
        for label_name in ["layak_jual", "tidak_layak_jual"]:
            (final_root / split_name / label_name).mkdir(parents=True, exist_ok=True)


def materialize_final_dataset(project_root: Path, final_root: Path, rows: list[dict[str, str]]) -> None:
    for row in rows:
        source_path = project_root / row["relative_path"]
        target_path = final_root / row["split"] / row["final_label"] / row["filename"]
        shutil.copy2(source_path, target_path)


def write_rows(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize_splits(rows: list[dict[str, str]]) -> dict[str, int]:
    summary: dict[str, int] = defaultdict(int)
    for row in rows:
        summary[row["split"]] += 1
    return dict(summary)


if __name__ == "__main__":
    raise SystemExit(main())
