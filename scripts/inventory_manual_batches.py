from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


FIELDNAMES = [
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

PRODUCT_DOMAIN_MAP = {
    "keripik": "keripik",
    "kerupuk": "kerupuk",
    "biskuit": "biskuit_kukis",
    "kukis": "biskuit_kukis",
    "stik": "stik",
}

LABEL_GUESS_MAP = {
    "sellable": "layak_jual",
    "non_sellable": "tidak_layak_jual",
}

ALLOWED_PRODUCTS = set(PRODUCT_DOMAIN_MAP)
ALLOWED_LABEL_LANES = set(LABEL_GUESS_MAP)


@dataclass(frozen=True)
class BatchImageRow:
    product_name: str
    label_lane: str
    batch_name: str
    filename: str
    relative_path: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inventory manual incoming image batches from dataset-scrape workspace.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path for umkm-food-quality.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="Path to dataset-scrape incoming root.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output CSV path for the manual batch inventory.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    source_root = args.source_root.resolve() if args.source_root else project_root.parents[0] / "dataset-scrape" / "scraped" / "incoming"
    output_csv = args.output_csv.resolve() if args.output_csv else project_root / "dataset" / "metadata" / "manual_incoming_inventory.csv"

    rows = collect_rows(source_root, project_root)
    write_csv(output_csv, rows)

    print(f"Manual inventory rows written: {len(rows)}")
    print(f"Source root: {source_root}")
    print(f"Output CSV: {output_csv}")
    return 0


def collect_rows(source_root: Path, project_root: Path) -> list[dict[str, str]]:
    if not source_root.exists():
        raise FileNotFoundError(f"Source root does not exist: {source_root}")

    image_rows: list[BatchImageRow] = []
    for product_dir in sorted(source_root.iterdir()):
        if not product_dir.is_dir() or product_dir.name.startswith("."):
            continue
        product_name = product_dir.name
        if product_name not in ALLOWED_PRODUCTS:
            raise ValueError(f"Unsupported product folder: {product_name}")

        for lane_dir in sorted(product_dir.iterdir()):
            if not lane_dir.is_dir() or lane_dir.name.startswith("."):
                continue
            label_lane = lane_dir.name
            if label_lane not in ALLOWED_LABEL_LANES:
                print(
                    f"Skipping unsupported label lane: {product_name}/{label_lane}",
                    file=sys.stderr,
                )
                continue

            direct_images = [
                image_path
                for image_path in sorted(lane_dir.iterdir())
                if image_path.is_file() and not image_path.name.startswith(".")
            ]
            if direct_images:
                image_rows.extend(
                    BatchImageRow(
                        product_name=product_name,
                        label_lane=label_lane,
                        batch_name="batch_01",
                        filename=image_path.name,
                        relative_path=str(image_path.relative_to(project_root.parents[0])).replace("\\", "/"),
                    )
                    for image_path in direct_images
                )
                continue

            for batch_dir in sorted(lane_dir.iterdir()):
                if not batch_dir.is_dir() or batch_dir.name.startswith("."):
                    continue
                batch_name = batch_dir.name

                for image_path in sorted(batch_dir.iterdir()):
                    if not image_path.is_file() or image_path.name.startswith("."):
                        continue
                    image_rows.append(
                        BatchImageRow(
                            product_name=product_name,
                            label_lane=label_lane,
                            batch_name=batch_name,
                            filename=image_path.name,
                            relative_path=str(image_path.relative_to(project_root.parents[0])).replace("\\", "/"),
                        )
                    )

    inventory_rows: list[dict[str, str]] = []
    for index, row in enumerate(image_rows, start=1):
        inventory_rows.append(
            {
                "image_id": f"manual_batch_{index:06d}",
                "source_type": "manual",
                "source_batch": f"{row.product_name}_{row.label_lane}_{row.batch_name}",
                "dataset_name": "dataset-scrape",
                "dataset_slug": "dataset_scrape_manual",
                "source_group": "manual_batch",
                "product_name": row.product_name,
                "product_domain": PRODUCT_DOMAIN_MAP[row.product_name],
                "label_lane": row.label_lane,
                "final_label_guess": LABEL_GUESS_MAP[row.label_lane],
                "batch_name": row.batch_name,
                "filename": row.filename,
                "relative_path": row.relative_path,
                "source_workspace": "dataset-scrape",
                "review_status": "incoming",
                "notes": "Imported from manual incoming batch inventory.",
            }
        )
    return inventory_rows


def write_csv(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
