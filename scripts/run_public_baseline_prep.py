from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full public baseline preparation pipeline.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root path.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=PROJECT_ROOT.parents[0] / "dataset",
        help="Source dataset root outside the project.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=224,
        help="Output square image size for preprocessing.",
    )
    parser.add_argument(
        "--skip-preprocess",
        action="store_true",
        help="Skip the preprocessing step and only regenerate metadata, split, and audit outputs.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    source_root = args.source_root.resolve()

    ml_python = project_root / ".venv-ml" / "bin" / "python"
    if not ml_python.exists():
        raise SystemExit(f"Missing ML interpreter: {ml_python}")

    commands = []
    if not args.skip_preprocess:
        commands.append(
            [
                str(ml_python),
                "scripts/clean_public_datasets.py",
                "--source-root",
                str(source_root),
                "--image-size",
                str(args.image_size),
            ]
        )

    commands.extend(
        [
            [str(ml_python), "scripts/generate_metadata.py"],
            [str(ml_python), "scripts/split_dataset.py"],
            [str(ml_python), "scripts/check_class_balance.py"],
        ]
    )

    executed = []
    for command in commands:
        print(f"Running: {' '.join(command)}")
        subprocess.run(command, cwd=project_root, check=True)
        executed.append(command)

    summary = build_summary(project_root, executed)
    summary_path = project_root / "dataset" / "metadata" / "public_baseline_prep_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Summary written: {summary_path}")
    print(f"Normalized images: {summary['normalized_images']}")
    print(f"Merged public images: {summary['merged_public_images']}")
    print(f"Public metadata rows: {summary['public_metadata_rows']}")
    print(f"Split metadata rows: {summary['split_metadata_rows']}")
    return 0


def build_summary(project_root: Path, executed_commands: list[list[str]]) -> dict[str, object]:
    normalized_images = sum(1 for _ in (project_root / "dataset" / "working" / "normalized").rglob("*.jpg"))
    merged_public_images = sum(1 for _ in (project_root / "dataset" / "working" / "merged_public").rglob("*.jpg"))
    public_metadata_rows = count_csv_rows(project_root / "dataset" / "metadata" / "public_metadata.csv")
    split_metadata_rows = count_csv_rows(project_root / "dataset" / "metadata" / "split_metadata.csv")
    return {
        "executed_commands": executed_commands,
        "normalized_images": normalized_images,
        "merged_public_images": merged_public_images,
        "public_metadata_rows": public_metadata_rows,
        "split_metadata_rows": split_metadata_rows,
    }


def count_csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as file_obj:
        return max(sum(1 for _ in file_obj) - 1, 0)


if __name__ == "__main__":
    raise SystemExit(main())
