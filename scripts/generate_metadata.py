from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDNAMES = [
    "image_id",
    "filename",
    "relative_path",
    "dataset_name",
    "dataset_slug",
    "source_type",
    "product_domain",
    "final_label",
    "source_group",
    "review_status",
    "split",
]


DATASET_DETAILS = {
    "industry_biscuit": {
        "dataset_name": "IndustryBiscuit",
        "product_domain": "biskuit_kukis",
        "source_group": "public_dataset",
    },
    "pepsico_potato_lab": {
        "dataset_name": "Pepsico RnD Potato Lab Dataset",
        "product_domain": "keripik",
        "source_group": "public_dataset",
    },
    "taterdat_chip": {
        "dataset_name": "taterdat-chip",
        "product_domain": "keripik",
        "source_group": "public_dataset",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate metadata CSV for normalized public datasets.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    parser.add_argument(
        "--normalized-root",
        type=Path,
        default=None,
        help="Path to normalized public dataset root.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output CSV path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    normalized_root = args.normalized_root.resolve() if args.normalized_root else project_root / "dataset" / "working" / "normalized"
    output_csv = args.output_csv.resolve() if args.output_csv else project_root / "dataset" / "metadata" / "public_metadata.csv"

    rows = collect_rows(normalized_root, project_root)
    write_csv(output_csv, rows)

    print(f"Metadata rows written: {len(rows)}")
    print(f"Output CSV: {output_csv}")
    return 0


def collect_rows(normalized_root: Path, project_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    counter = 0

    for dataset_dir in sorted(normalized_root.iterdir()):
        if not dataset_dir.is_dir():
            continue
        dataset_slug = dataset_dir.name
        if dataset_slug not in DATASET_DETAILS:
            raise ValueError(f"Unsupported dataset slug: {dataset_slug}")

        details = DATASET_DETAILS[dataset_slug]
        for label_dir in sorted(dataset_dir.iterdir()):
            if not label_dir.is_dir():
                continue
            final_label = label_dir.name
            for image_path in sorted(label_dir.glob("*.jpg")):
                counter += 1
                rows.append(
                    {
                        "image_id": f"public_{counter:06d}",
                        "filename": image_path.name,
                        "relative_path": str(image_path.relative_to(project_root)).replace("\\", "/"),
                        "dataset_name": details["dataset_name"],
                        "dataset_slug": dataset_slug,
                        "source_type": "public",
                        "product_domain": details["product_domain"],
                        "final_label": final_label,
                        "source_group": details["source_group"],
                        "review_status": "approved",
                        "split": "",
                    }
                )

    return rows


def write_csv(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
