from __future__ import annotations

import argparse
import csv
from pathlib import Path


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
    "final_label_guess",
    "batch_name",
    "filename",
    "relative_path",
    "source_workspace",
    "review_status",
    "notes",
]

OUTPUT_FIELDNAMES = [
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

TRAINING_LABEL_MAP = {
    "sellable": "layak_jual",
    "non_sellable": "tidak_layak_jual",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize manual lane labels into training classes.")
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
        help="Input CSV path for manual incoming inventory.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output CSV path for normalized manual training labels.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    input_csv = args.input_csv.resolve() if args.input_csv else project_root / "dataset" / "metadata" / "manual_incoming_inventory.csv"
    output_csv = args.output_csv.resolve() if args.output_csv else project_root / "dataset" / "metadata" / "manual_training_labels.csv"

    rows = read_rows(input_csv)
    normalized_rows = normalize_rows(rows)
    write_rows(output_csv, normalized_rows)

    print(f"Input rows normalized: {len(rows)}")
    print(f"Output rows written: {len(normalized_rows)}")
    print(f"Output CSV: {output_csv}")
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


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        label_lane = row["label_lane"]
        if label_lane not in TRAINING_LABEL_MAP:
            raise ValueError(f"Unsupported label lane: {label_lane}")

        notes = row.get("notes", "")
        notes = append_note(notes, f"Training label normalized from lane '{label_lane}'.")

        normalized_rows.append(
            {
                "image_id": row["image_id"],
                "source_type": row["source_type"],
                "source_batch": row["source_batch"],
                "dataset_name": row["dataset_name"],
                "dataset_slug": row["dataset_slug"],
                "source_group": row["source_group"],
                "product_name": row["product_name"],
                "product_domain": row["product_domain"],
                "label_lane": label_lane,
                "training_label": TRAINING_LABEL_MAP[label_lane],
                "batch_name": row["batch_name"],
                "filename": row["filename"],
                "relative_path": row["relative_path"],
                "source_workspace": row["source_workspace"],
                "review_status": row["review_status"],
                "notes": notes,
            }
        )
    return normalized_rows


def append_note(existing: str, extra: str) -> str:
    if not existing:
        return extra
    return f"{existing} {extra}"


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
