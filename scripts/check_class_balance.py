from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit label balance and domain gaps for public datasets.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    parser.add_argument(
        "--metadata-csv",
        type=Path,
        default=None,
        help="Input metadata CSV path.",
    )
    parser.add_argument(
        "--split-csv",
        type=Path,
        default=None,
        help="Input split metadata CSV path.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    metadata_csv = args.metadata_csv.resolve() if args.metadata_csv else project_root / "dataset" / "metadata" / "public_metadata.csv"
    split_csv = args.split_csv.resolve() if args.split_csv else project_root / "dataset" / "metadata" / "split_metadata.csv"
    output_md = args.output_md.resolve() if args.output_md else project_root / "docs" / "dataset_gap_notes.md"

    metadata_rows = read_rows(metadata_csv)
    split_rows = read_rows(split_csv)

    report = build_report(metadata_rows, split_rows)
    output_md.write_text(report, encoding="utf-8")

    print(f"Metadata rows: {len(metadata_rows)}")
    print(f"Split rows: {len(split_rows)}")
    print(f"Report written: {output_md}")
    return 0


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def build_report(metadata_rows: list[dict[str, str]], split_rows: list[dict[str, str]]) -> str:
    total_label_counts = Counter(row["final_label"] for row in metadata_rows)
    dataset_label_counts: dict[str, Counter[str]] = defaultdict(Counter)
    product_domain_counts: dict[str, Counter[str]] = defaultdict(Counter)
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for row in metadata_rows:
        dataset_label_counts[row["dataset_slug"]][row["final_label"]] += 1
        product_domain_counts[row["product_domain"]][row["final_label"]] += 1

    for row in split_rows:
        split_counts[row["split"]][row["final_label"]] += 1

    missing_domains = compute_missing_domains(product_domain_counts)
    observations = build_observations(total_label_counts, dataset_label_counts, product_domain_counts, split_counts, missing_domains)

    lines = [
        "# Dataset Gap Notes",
        "",
        "Dokumen ini merangkum audit balance label dan gap domain untuk baseline public datasets.",
        "",
        "## Total Label Balance",
        "",
        "| Label | Count |",
        "|---|---:|",
    ]

    for label_name in sorted(total_label_counts):
        lines.append(f"| `{label_name}` | {total_label_counts[label_name]} |")

    lines.extend([
        "",
        "## Balance per Dataset Source",
        "",
        "| Dataset Slug | Layak Jual | Tidak Layak Jual |",
        "|---|---:|---:|",
    ])

    for dataset_slug in sorted(dataset_label_counts):
        counts = dataset_label_counts[dataset_slug]
        lines.append(
            f"| `{dataset_slug}` | {counts.get('layak_jual', 0)} | {counts.get('tidak_layak_jual', 0)} |"
        )

    lines.extend([
        "",
        "## Balance per Product Domain",
        "",
        "| Product Domain | Layak Jual | Tidak Layak Jual |",
        "|---|---:|---:|",
    ])

    for product_domain in sorted(product_domain_counts):
        counts = product_domain_counts[product_domain]
        lines.append(
            f"| `{product_domain}` | {counts.get('layak_jual', 0)} | {counts.get('tidak_layak_jual', 0)} |"
        )

    lines.extend([
        "",
        "## Split Coverage",
        "",
        "| Split | Layak Jual | Tidak Layak Jual |",
        "|---|---:|---:|",
    ])

    for split_name in ["train", "val", "test"]:
        counts = split_counts.get(split_name, Counter())
        lines.append(
            f"| `{split_name}` | {counts.get('layak_jual', 0)} | {counts.get('tidak_layak_jual', 0)} |"
        )

    lines.extend([
        "",
        "## Missing or Deferred Domains",
        "",
    ])

    if missing_domains:
        for domain_name in missing_domains:
            lines.append(f"- `{domain_name}` belum punya coverage publik aktif di baseline saat ini.")
    else:
        lines.append("- Tidak ada domain aktif yang benar-benar kosong di metadata publik saat ini.")

    lines.extend([
        "",
        "## Key Observations",
        "",
    ])

    for observation in observations:
        lines.append(f"- {observation}")

    return "\n".join(lines) + "\n"


def compute_missing_domains(product_domain_counts: dict[str, Counter[str]]) -> list[str]:
    expected_domains = {"biskuit_kukis", "keripik", "kerupuk"}
    present_domains = {domain_name for domain_name, counts in product_domain_counts.items() if sum(counts.values()) > 0}
    return sorted(expected_domains - present_domains)


def build_observations(
    total_label_counts: Counter[str],
    dataset_label_counts: dict[str, Counter[str]],
    product_domain_counts: dict[str, Counter[str]],
    split_counts: dict[str, Counter[str]],
    missing_domains: list[str],
) -> list[str]:
    observations: list[str] = []

    layak_count = total_label_counts.get("layak_jual", 0)
    tidak_layak_count = total_label_counts.get("tidak_layak_jual", 0)
    if layak_count == tidak_layak_count:
        observations.append("Total label publik saat ini masih seimbang antara layak_jual dan tidak_layak_jual.")
    else:
        observations.append("Total label publik saat ini belum seimbang dan perlu dipantau saat dataset diperbesar.")

    if "kerupuk" in missing_domains:
        observations.append("Domain kerupuk masih kosong dan tetap menjadi gap utama yang harus ditutup oleh data primer lokal.")

    keripik_sources = [slug for slug in dataset_label_counts if slug in {"pepsico_potato_lab", "taterdat_chip"}]
    if len(keripik_sources) == 2:
        observations.append("Domain keripik sudah punya dua sumber publik berbeda, sehingga baseline gabungan keripik layak diuji di fase eksperimen berikutnya.")

    biskuit_count = sum(product_domain_counts.get("biskuit_kukis", Counter()).values())
    if biskuit_count > 0:
        observations.append("Domain biskuit_kukis masih bertumpu pada satu sumber utama, sehingga validasi domain lintas sumber nanti tetap penting.")

    if split_counts.get("val", Counter()).total() == 0 or split_counts.get("test", Counter()).total() == 0:
        observations.append("Split validation dan test masih kosong pada smoke-test ini, yang normal karena ukuran bucket per sumber-label masih sangat kecil.")

    return observations


if __name__ == "__main__":
    raise SystemExit(main())
