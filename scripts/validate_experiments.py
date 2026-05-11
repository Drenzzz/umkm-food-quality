from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_ROOT_KEYS = {
    "experiment_id",
    "experiment_name",
    "status",
    "goal",
    "dataset_scope",
    "training_plan",
}
REQUIRED_SCOPE_KEYS = {"dataset_slugs", "product_domains", "allowed_labels"}
REQUIRED_TRAINING_KEYS = {
    "input_metadata",
    "split_metadata",
    "model_family",
    "evaluation_priority",
}
VALID_DATASET_SLUGS = {"industry_biscuit", "taterdat_chip", "pepsico_potato_lab"}
VALID_PRODUCT_DOMAINS = {"biskuit_kukis", "keripik"}
VALID_LABELS = {"layak_jual", "tidak_layak_jual"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate planned baseline experiment definitions.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    experiments_dir = project_root / "ml" / "experiments"
    metadata_path = project_root / "dataset" / "metadata" / "public_metadata.csv"
    split_path = project_root / "dataset" / "metadata" / "split_metadata.csv"

    experiment_paths = sorted(experiments_dir.glob("exp_*.json"))
    if not experiment_paths:
        raise SystemExit("No experiment definition files were found.")

    for path in experiment_paths:
        validate_experiment_file(path, metadata_path, split_path)

    print(f"Validated experiments: {len(experiment_paths)}")
    for path in experiment_paths:
        print(path.name)
    return 0


def validate_experiment_file(path: Path, metadata_path: Path, split_path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))

    missing_root_keys = REQUIRED_ROOT_KEYS - payload.keys()
    if missing_root_keys:
        raise ValueError(f"{path.name}: missing root keys {sorted(missing_root_keys)}")

    scope = payload["dataset_scope"]
    missing_scope_keys = REQUIRED_SCOPE_KEYS - scope.keys()
    if missing_scope_keys:
        raise ValueError(f"{path.name}: missing scope keys {sorted(missing_scope_keys)}")

    training_plan = payload["training_plan"]
    missing_training_keys = REQUIRED_TRAINING_KEYS - training_plan.keys()
    if missing_training_keys:
        raise ValueError(f"{path.name}: missing training keys {sorted(missing_training_keys)}")

    if not set(scope["dataset_slugs"]).issubset(VALID_DATASET_SLUGS):
        raise ValueError(f"{path.name}: contains unsupported dataset slug")
    if not set(scope["product_domains"]).issubset(VALID_PRODUCT_DOMAINS):
        raise ValueError(f"{path.name}: contains unsupported product domain")
    if set(scope["allowed_labels"]) != VALID_LABELS:
        raise ValueError(f"{path.name}: allowed labels must match binary baseline labels")

    if training_plan["input_metadata"] != str(metadata_path.relative_to(path.parents[2])).replace("\\", "/"):
        raise ValueError(f"{path.name}: input_metadata path is not aligned with project metadata")
    if training_plan["split_metadata"] != str(split_path.relative_to(path.parents[2])).replace("\\", "/"):
        raise ValueError(f"{path.name}: split_metadata path is not aligned with project metadata")


if __name__ == "__main__":
    raise SystemExit(main())
