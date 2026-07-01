"""
Dataset integrity audit — deduplication and label quality check.

Outputs:
    ml/reports/dataset_integrity_report.json
    ml/reports/dedup_duplicates.json       (near-duplicate pairs)
    ml/reports/label_issues.json           (potential mislabels)

Usage:
    python -m ml.audit_dataset --project-root .
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "ml" / "reports"


def load_split_metadata(metadata_path: Path) -> list[dict[str, str]]:
    import csv

    rows: list[dict[str, str]] = []
    with metadata_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def resolve_image_path(row: dict[str, str], project_root: Path) -> Path | None:
    candidate = project_root / row["relative_path"]
    if candidate.exists():
        return candidate
    return None


# ---------------------------------------------------------------------------
# Phase 1: Near-duplicate detection via imagededup
# ---------------------------------------------------------------------------

def run_dedup_audit(rows: list[dict[str, str]], project_root: Path) -> dict:
    from imagededup.methods import PHash

    logger.info("Phase 1: Running near-duplicate detection (PHash) ...")

    # encode_images() in imagededup 0.3.x only accepts image_dir, not image_map.
    # Point to the normalized dataset root which contains all images recursively.
    dataset_root = project_root / "dataset" / "working" / "manual_normalized"
    if not dataset_root.exists():
        logger.warning("Dataset root not found: %s — skipping dedup", dataset_root)
        return _empty_dedup_report()

    phasher = PHash()
    encodings = phasher.encode_images(image_dir=dataset_root, recursive=True)

    duplicates = phasher.find_duplicates(
        encoding_map=encodings,
        max_distance_threshold=10,
        scores=True,
    )

    # Build a lookup from filename -> metadata row for split/label info
    # encodings keys are filenames like "manual_20cb4bf2594e.jpg"
    file_to_row: dict[str, dict[str, str]] = {}
    for row in rows:
        fname = Path(row["relative_path"]).name
        file_to_row[fname] = row

    cross_split_pairs: list[dict] = []
    same_split_pairs: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for img_file, matches in duplicates.items():
        if not matches:
            continue
        for match_file, distance in matches:
            pair = tuple(sorted([img_file, match_file]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            row_a = file_to_row.get(img_file, {})
            row_b = file_to_row.get(match_file, {})

            split_a = row_a.get("split", "unknown")
            split_b = row_b.get("split", "unknown")
            label_a = row_a.get("final_label", "unknown")
            label_b = row_b.get("final_label", "unknown")

            entry = {
                "image_a": img_file,
                "image_b": match_file,
                "distance": distance,
                "split_a": split_a,
                "split_b": split_b,
                "label_a": label_a,
                "label_b": label_b,
            }

            if split_a != split_b:
                cross_split_pairs.append(entry)
            else:
                same_split_pairs.append(entry)

    report = {
        "total_images_indexed": len(encodings),
        "images_missing_from_disk": 0,
        "total_near_duplicate_pairs": len(seen_pairs),
        "cross_split_duplicates": len(cross_split_pairs),
        "same_split_duplicates": len(same_split_pairs),
        "leakage_detected": len(cross_split_pairs) > 0,
        "cross_split_pairs": cross_split_pairs,
        "same_split_pairs_summary": same_split_pairs[:50],
    }

    logger.info("  Indexed %d images, found %d duplicate pairs", len(encodings), len(seen_pairs))
    logger.info("  Cross-split (LEAKAGE): %d pairs", len(cross_split_pairs))
    logger.info("  Same-split: %d pairs", len(same_split_pairs))

    return report


def _empty_dedup_report() -> dict:
    return {
        "total_images_indexed": 0,
        "images_missing_from_disk": 0,
        "total_near_duplicate_pairs": 0,
        "cross_split_duplicates": 0,
        "same_split_duplicates": 0,
        "leakage_detected": False,
        "cross_split_pairs": [],
        "same_split_pairs_summary": [],
    }


# ---------------------------------------------------------------------------
# Phase 2: Label quality via cleanlab
# ---------------------------------------------------------------------------

def run_label_audit(rows: list[dict[str, str]], project_root: Path) -> dict:
    from cleanlab import filter

    import numpy as np

    logger.info("Phase 2: Running label quality audit (cleanlab) ...")

    label_to_idx = {"layak_jual": 0, "tidak_layak_jual": 1}

    valid_rows = [r for r in rows if resolve_image_path(r, project_root) is not None]
    if not valid_rows:
        return {"error": "No valid images found"}

    labels = np.array([label_to_idx.get(r["final_label"], -1) for r in valid_rows])

    # Use model confidence scores as proxy for cleanlab (requires a model).
    # Since we don't have pre-computed probabilities here, we use a simpler
    # approach: run the active model on the dataset and collect softmax probs.
    probs = _collect_model_predictions(valid_rows, project_root)

    if probs is None:
        return {"error": "Could not load model for label audit"}

    # Find label issues using cleanlab's rank
    label_issues = filter.find_label_issues(
        labels=labels,
        pred_probs=probs,
        return_indices_ranked_by="self_confidence",
    )

    issue_list = []
    for idx in label_issues:
        row = valid_rows[idx]
        issue_list.append({
            "image_id": row["image_id"],
            "relative_path": row["relative_path"],
            "given_label": row["final_label"],
            "split": row["split"],
            "product_domain": row.get("product_domain", "unknown"),
        })

    report = {
        "total_evaluated": len(valid_rows),
        "potential_label_issues": len(issue_list),
        "issues": issue_list,
    }

    logger.info("  Evaluated %d images, found %d potential label issues", len(valid_rows), len(issue_list))

    return report


def _collect_model_predictions(rows: list[dict[str, str]], project_root: Path) -> "np.ndarray | None":
    import numpy as np

    try:
        import tensorflow as tf
        from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
        from PIL import Image
    except ImportError:
        logger.warning("  TensorFlow not available — skipping model-based label audit")
        return None

    active_model_path = project_root / "ml" / "model" / "active_model.json"
    if not active_model_path.exists():
        logger.warning("  active_model.json not found — skipping label audit")
        return None

    active = json.loads(active_model_path.read_text(encoding="utf-8"))
    model_file = project_root / active.get("model_path", "ml/model/umkm_food_quality_v1/model.keras")
    if not model_file.exists():
        logger.warning("  Model file not found at %s", model_file)
        return None

    model = tf.keras.models.load_model(model_file)
    predictions: list[np.ndarray] = []

    for row in rows:
        img_path = project_root / row["relative_path"]
        try:
            with Image.open(img_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img = img.resize((224, 224), resample=Image.Resampling.LANCZOS)
                arr = np.asarray(img, dtype=np.float32)
            arr = np.expand_dims(arr, axis=0)
            arr = preprocess_input(arr)
            prob = model.predict(arr, verbose=0).flatten()[0]
            # Convert sigmoid output to 2-class probs: [1-prob, prob] for [layak, tidak_layak]
            predictions.append(np.array([1.0 - prob, prob]))
        except Exception as exc:
            logger.warning("  Failed to predict %s: %s", img_path, exc)
            predictions.append(np.array([0.5, 0.5]))

    return np.array(predictions)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Dataset integrity audit")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    metadata_path = project_root / "dataset" / "metadata" / "manual_split_metadata.csv"

    if not metadata_path.exists():
        logger.error("Metadata not found: %s", metadata_path)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_split_metadata(metadata_path)
    logger.info("Loaded %d rows from metadata", len(rows))

    dedup_report = run_dedup_audit(rows, project_root)
    (REPORTS_DIR / "dedup_duplicates.json").write_text(
        json.dumps(dedup_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    label_report = run_label_audit(rows, project_root)
    (REPORTS_DIR / "label_issues.json").write_text(
        json.dumps(label_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    combined = {
        "dataset_path": str(metadata_path),
        "total_rows": len(rows),
        "dedup": {
            "total_near_duplicate_pairs": dedup_report["total_near_duplicate_pairs"],
            "cross_split_duplicates": dedup_report["cross_split_duplicates"],
            "leakage_detected": dedup_report["leakage_detected"],
        },
        "label_quality": {
            "total_evaluated": label_report.get("total_evaluated", 0),
            "potential_label_issues": label_report.get("potential_label_issues", 0),
        },
    }

    (REPORTS_DIR / "dataset_integrity_report.json").write_text(
        json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info("=" * 60)
    logger.info("AUDIT COMPLETE")
    logger.info("  Near-duplicate pairs: %d (cross-split: %d)", dedup_report["total_near_duplicate_pairs"], dedup_report["cross_split_duplicates"])
    logger.info("  Potential label issues: %d", label_report.get("potential_label_issues", 0))
    logger.info("  Reports saved to: %s", REPORTS_DIR)
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
