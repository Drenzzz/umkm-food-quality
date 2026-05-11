from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.artifacts import ensure_manifest, relative_to_model_dir, save_manifest, utc_now_iso


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh artifact manifest from files already present in a model directory.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="Experiment identifier without file extension.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    experiment_path = project_root / "ml" / "experiments" / f"{args.experiment}.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))

    model_dir = project_root / "ml" / "model" / args.experiment
    evaluation_dir = model_dir / "evaluation"
    split_metadata = project_root / experiment["training_plan"]["split_metadata"]

    manifest = ensure_manifest(model_dir, experiment["experiment_id"], experiment["training_plan"]["model_family"])

    file_candidates = {
        "model": model_dir / "model.keras",
        "class_indices": model_dir / "class_indices.json",
        "training_history": model_dir / "training_history.json",
        "training_log": model_dir / "training_log.csv",
        "evaluation_report": evaluation_dir / "evaluation_report.json",
        "confusion_matrix": evaluation_dir / "confusion_matrix.png",
        "threshold_review": evaluation_dir / "threshold_review.json",
    }

    for key, path in file_candidates.items():
        if path.exists():
            manifest.files[key] = relative_to_model_dir(model_dir, path)

    if (model_dir / "model.keras").exists():
        manifest.status = "trained"
        manifest.training = {
            "split_metadata": str(split_metadata.relative_to(project_root)).replace("\\", "/"),
            "weights": manifest.training.get("weights", "unknown"),
            "refreshed_at": utc_now_iso(),
        }

    if (evaluation_dir / "evaluation_report.json").exists():
        report = json.loads((evaluation_dir / "evaluation_report.json").read_text(encoding="utf-8"))
        manifest.evaluation = {
            "used_split": report.get("used_split", "unknown"),
            "threshold": report.get("threshold", 0.5),
            "sample_count": report.get("sample_count", 0),
            "priority_metric": report.get("metrics", {}).get("recall_tidak_layak_jual") is not None and "recall_tidak_layak_jual" or "unknown",
            "refreshed_at": utc_now_iso(),
        }

    if (evaluation_dir / "threshold_review.json").exists():
        threshold_review = json.loads((evaluation_dir / "threshold_review.json").read_text(encoding="utf-8"))
        manifest.threshold_review = {
            "used_split": threshold_review.get("used_split", "unknown"),
            "priority_metric": threshold_review.get("priority_metric", "unknown"),
            "recommended_threshold": threshold_review.get("recommended_threshold", {}).get("threshold", 0.5),
            "threshold_count": len(threshold_review.get("thresholds", [])),
            "refreshed_at": utc_now_iso(),
        }

    save_manifest(model_dir, manifest)
    print(f"Manifest refreshed: {model_dir / 'artifact_manifest.json'}")
    print(f"Tracked files: {len(manifest.files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
