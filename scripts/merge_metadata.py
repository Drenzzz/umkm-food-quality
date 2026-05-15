from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDNAMES = [
    "image_id",
    "source_type",
    "source_batch",
    "submitted_at",
    "nama_pengirim",
    "nomor_whatsapp",
    "nama_usaha",
    "nama_produk",
    "jenis_produk",
    "jenis_produk_detail",
    "product_domain",
    "is_sold_product",
    "label_form",
    "jenis_cacat_form",
    "catatan_cacat",
    "file_url",
    "file_name",
    "filename",
    "relative_path",
    "dataset_name",
    "dataset_slug",
    "source_group",
    "notes",
    "consent_status",
    "label_review",
    "jenis_cacat_review",
    "review_status",
    "split",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge public and primary image metadata into one canonical CSV.")
    parser.add_argument("--public-csv", type=Path, required=True, help="Public metadata CSV path.")
    parser.add_argument("--primary-csv", type=Path, required=True, help="Primary metadata CSV path.")
    parser.add_argument("--output-csv", type=Path, required=True, help="Output merged metadata CSV path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    public_rows = read_rows(args.public_csv)
    primary_rows = read_rows(args.primary_csv)
    merged_rows = normalize_public_rows(public_rows) + normalize_primary_rows(primary_rows)
    write_rows(args.output_csv, merged_rows)
    print(f"Public rows merged: {len(public_rows)}")
    print(f"Primary rows merged: {len(primary_rows)}")
    print(f"Total merged rows: {len(merged_rows)}")
    print(f"Output CSV: {args.output_csv}")
    return 0


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def normalize_public_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "image_id": row["image_id"],
                "source_type": row.get("source_type", "public"),
                "source_batch": "public-baseline",
                "submitted_at": "",
                "nama_pengirim": "",
                "nomor_whatsapp": "",
                "nama_usaha": "",
                "nama_produk": "",
                "jenis_produk": "",
                "jenis_produk_detail": "",
                "product_domain": row.get("product_domain", ""),
                "is_sold_product": "",
                "label_form": row.get("final_label", ""),
                "jenis_cacat_form": "",
                "catatan_cacat": "",
                "file_url": "",
                "file_name": "",
                "filename": row.get("filename", ""),
                "relative_path": row.get("relative_path", ""),
                "dataset_name": row.get("dataset_name", ""),
                "dataset_slug": row.get("dataset_slug", ""),
                "source_group": row.get("source_group", "public_dataset"),
                "notes": "",
                "consent_status": "not_required",
                "label_review": row.get("final_label", ""),
                "jenis_cacat_review": "",
                "review_status": row.get("review_status", "approved"),
                "split": row.get("split", ""),
            }
        )
    return normalized


def normalize_primary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "image_id": row.get("image_id", ""),
                "source_type": row.get("source_type", "primary"),
                "source_batch": row.get("source_batch", ""),
                "submitted_at": row.get("submitted_at", ""),
                "nama_pengirim": row.get("nama_pengirim", ""),
                "nomor_whatsapp": row.get("nomor_whatsapp", ""),
                "nama_usaha": row.get("nama_usaha", ""),
                "nama_produk": row.get("nama_produk", ""),
                "jenis_produk": row.get("jenis_produk", ""),
                "jenis_produk_detail": row.get("jenis_produk_detail", ""),
                "product_domain": map_primary_domain(row.get("jenis_produk", "")),
                "is_sold_product": row.get("is_sold_product", ""),
                "label_form": row.get("label_form", ""),
                "jenis_cacat_form": row.get("jenis_cacat_form", ""),
                "catatan_cacat": row.get("catatan_cacat", ""),
                "file_url": row.get("file_url", ""),
                "file_name": row.get("file_name", ""),
                "filename": "",
                "relative_path": "",
                "dataset_name": "primary_data",
                "dataset_slug": "primary_data",
                "source_group": "form",
                "notes": row.get("notes", ""),
                "consent_status": row.get("consent_status", ""),
                "label_review": row.get("label_review", ""),
                "jenis_cacat_review": row.get("jenis_cacat_review", ""),
                "review_status": row.get("review_status", "pending_review"),
                "split": row.get("split", ""),
            }
        )
    return normalized


def map_primary_domain(jenis_produk: str) -> str:
    mapping = {
        "biskuit": "biskuit_kukis",
        "kukis": "biskuit_kukis",
        "keripik": "keripik",
        "kerupuk": "kerupuk",
    }
    return mapping.get(jenis_produk, jenis_produk)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
