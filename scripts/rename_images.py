from __future__ import annotations

import argparse
from pathlib import Path


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rename image files in a target directory with a stable prefix.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Input directory containing image files.")
    parser.add_argument("--prefix", required=True, help="Filename prefix for renamed images.")
    parser.add_argument("--start-number", type=int, default=1, help="Starting number for the rename sequence.")
    parser.add_argument("--digits", type=int, default=6, help="Zero-padding width for image numbering.")
    parser.add_argument("--dry-run", action="store_true", help="Preview rename operations without writing files.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    files = collect_files(args.input_dir)
    pairs = build_pairs(files, args.prefix, args.start_number, args.digits)

    for source_path, target_path in pairs:
        print(f"{source_path.name} -> {target_path.name}")

    if args.dry_run:
        print(f"Preview only. Files matched: {len(pairs)}")
        return 0

    apply_renames(pairs)
    print(f"Files renamed: {len(pairs)}")
    return 0


def collect_files(input_dir: Path) -> list[Path]:
    return sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS
    )


def build_pairs(files: list[Path], prefix: str, start_number: int, digits: int) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for index, source_path in enumerate(files, start=start_number):
        target_name = f"{prefix}_{index:0{digits}d}{source_path.suffix.lower()}"
        pairs.append((source_path, source_path.with_name(target_name)))
    return pairs


def apply_renames(pairs: list[tuple[Path, Path]]) -> None:
    temp_pairs: list[tuple[Path, Path]] = []
    for source_path, target_path in pairs:
        temp_path = source_path.with_name(f".__tmp__{source_path.name}")
        source_path.rename(temp_path)
        temp_pairs.append((temp_path, target_path))

    for temp_path, target_path in temp_pairs:
        temp_path.rename(target_path)


if __name__ == "__main__":
    raise SystemExit(main())
