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
    "is_sold_product",
    "label_form",
    "jenis_cacat_form",
    "catatan_cacat",
    "file_url",
    "file_name",
    "notes",
    "consent_status",
    "label_review",
    "jenis_cacat_review",
    "review_status",
    "split",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse form responses into image-level metadata rows.")
    parser.add_argument("--input-csv", type=Path, required=True, help="Raw Google Form response CSV path.")
    parser.add_argument("--output-csv", type=Path, required=True, help="Output image-level metadata CSV path.")
    parser.add_argument("--source-batch", required=True, help="Batch identifier for the parsed source data.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = read_form_rows(args.input_csv)
    image_rows = flatten_rows(rows, args.source_batch)
    write_rows(args.output_csv, image_rows)
    print(f"Responses parsed: {len(rows)}")
    print(f"Image rows written: {len(image_rows)}")
    print(f"Output CSV: {args.output_csv}")
    return 0


def read_form_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def flatten_rows(rows: list[dict[str, str]], source_batch: str) -> list[dict[str, str]]:
    image_rows: list[dict[str, str]] = []
    counter = 0

    for row in rows:
        file_urls = split_file_urls(row.get("Unggah Foto Produk", ""))
        if not file_urls:
            continue

        for file_url in file_urls:
            counter += 1
            image_rows.append(
                {
                    "image_id": f"form_{counter:06d}",
                    "source_type": "form",
                    "source_batch": source_batch,
                    "submitted_at": row.get("Timestamp", ""),
                    "nama_pengirim": row.get("Nama Lengkap", ""),
                    "nomor_whatsapp": row.get("Nomor WhatsApp", ""),
                    "nama_usaha": row.get("Nama Usaha / Merek Produk", ""),
                    "nama_produk": row.get("Nama Produk", ""),
                    "jenis_produk": normalize_product_name(row.get("Jenis Produk", "")),
                    "jenis_produk_detail": row.get('Jika memilih "Lainnya", tuliskan jenis produk', ""),
                    "is_sold_product": normalize_yes_no(row.get("Apakah produk ini biasanya dijual atau dipasarkan?", "")),
                    "label_form": normalize_label(row.get("Kondisi visual produk saat difoto", "")),
                    "jenis_cacat_form": normalize_defect(row.get("Jika produk dianggap tidak layak jual atau ragu, apa kondisi utamanya?", "")),
                    "catatan_cacat": row.get('Jika memilih "Lainnya", jelaskan kondisi produk', ""),
                    "file_url": file_url,
                    "file_name": "",
                    "notes": row.get("Keterangan tambahan mengenai produk atau foto", ""),
                    "consent_status": normalize_consent(row.get("Persetujuan penggunaan data", "")),
                    "label_review": "",
                    "jenis_cacat_review": "",
                    "review_status": "pending_review",
                    "split": "",
                }
            )

    return image_rows


def split_file_urls(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def normalize_product_name(value: str) -> str:
    mapping = {
        "Keripik": "keripik",
        "Kerupuk": "kerupuk",
        "Biskuit": "biskuit",
        "Kukis": "kukis",
        "Lainnya": "lainnya",
    }
    return mapping.get(value.strip(), value.strip().lower().replace(" ", "_"))


def normalize_yes_no(value: str) -> str:
    mapping = {
        "Ya": "yes",
        "Tidak": "no",
    }
    return mapping.get(value.strip(), "")


def normalize_label(value: str) -> str:
    mapping = {
        "Layak jual": "layak_jual",
        "Tidak layak jual": "tidak_layak_jual",
        "Ragu / tidak yakin": "ragu",
    }
    return mapping.get(value.strip(), "")


def normalize_defect(value: str) -> str:
    if not value.strip():
        return ""

    parts = [part.strip() for part in value.split(",") if part.strip()]
    normalized_parts = []
    for part in parts:
        normalized_parts.append(
            {
                "Gosong": "gosong",
                "Patah / remuk": "patah_remuk",
                "Warna tidak normal": "warna_tidak_normal",
                "Bercak / noda": "bercak_noda",
                "Bentuk tidak utuh": "bentuk_tidak_utuh",
                "Campuran beberapa cacat": "campuran",
                "Lainnya": "lainnya",
                "Tidak ada": "none",
            }.get(part, part.lower().replace(" ", "_"))
        )
    return ";".join(normalized_parts)


def normalize_consent(value: str) -> str:
    return "approved" if value.strip() else "missing"


def write_rows(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
