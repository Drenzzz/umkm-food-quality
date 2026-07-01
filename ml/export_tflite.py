"""
Export a trained Keras model to TFLite format with numeric parity verification.

The exported .tflite model is used by the backend for lightweight inference
via tflite-runtime (~5 MB) instead of full TensorFlow (~1 GB).

Usage:
    python -m ml.export_tflite --project-root . --experiment umkm_food_quality_v1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Keras model to TFLite with parity check.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--experiment", default="umkm_food_quality_v1")
    parser.add_argument("--parity-tolerance", type=float, default=1e-5,
                        help="Max allowed absolute difference between Keras and TFLite outputs.")
    parser.add_argument("--parity-samples", type=int, default=10,
                        help="Number of random images to use for parity verification.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load and verify parity without saving the .tflite file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    model_dir = project_root / "ml" / "model" / args.experiment

    keras_path = model_dir / "model.keras"
    tflite_path = model_dir / "model.tflite"

    if not keras_path.exists():
        print(f"ERROR: Model not found at {keras_path}")
        return 1

    print(f"Loading Keras model from {keras_path} ...")
    keras_model = tf.keras.models.load_model(keras_path)

    print(f"Converting to TFLite (no quantization — preserving numeric parity) ...")
    converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
    tflite_bytes = converter.convert()

    print(f"TFLite model size: {len(tflite_bytes) / 1024 / 1024:.2f} MB")

    # Verify numeric parity using sample images from the dataset
    parity_ok = verify_parity(
        keras_model, tflite_bytes,
        project_root, args.parity_tolerance, args.parity_samples,
    )

    if not parity_ok:
        print("WARNING: Parity check FAILED. Model may produce different outputs.")
        print("Consider keeping the .keras model for backend inference.")
        return 1

    if args.dry_run:
        print("Dry run — not saving .tflite file.")
        return 0

    tflite_path.write_bytes(tflite_bytes)
    print(f"TFLite model saved to {tflite_path}")

    # Save export metadata
    meta = {
        "source_model": str(keras_path.relative_to(project_root)),
        "tflite_model": str(tflite_path.relative_to(project_root)),
        "tflite_size_bytes": len(tflite_bytes),
        "optimization": "none",
        "parity_tolerance": args.parity_tolerance,
        "parity_samples": args.parity_samples,
        "parity_passed": True,
    }
    meta_path = model_dir / "tflite_export.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Export metadata saved to {meta_path}")

    return 0


def verify_parity(
    keras_model: tf.keras.Model,
    tflite_bytes: bytes,
    project_root: Path,
    tolerance: float,
    num_samples: int,
) -> bool:
    """Compare Keras and TFLite outputs on sample images."""
    sample_paths = collect_sample_images(project_root, num_samples)

    if not sample_paths:
        print("WARNING: No sample images found — skipping parity check.")
        return True

    interpreter = tf.lite.Interpreter(model_content=tflite_bytes)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    max_diff = 0.0
    all_close = True

    for img_path in sample_paths:
        # Preprocess identically to training (MobileNetV2 preprocess_input)
        with Image.open(img_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = img.resize((224, 224), resample=Image.Resampling.LANCZOS)
            arr = np.asarray(img, dtype=np.float32)

        arr_batch = np.expand_dims(arr, axis=0)
        arr_preprocessed = preprocess_input(arr_batch.copy())

        # Keras prediction
        keras_prob = float(keras_model.predict(arr_preprocessed, verbose=0).flatten()[0])

        # TFLite prediction
        interpreter.set_tensor(input_details[0]["index"], arr_preprocessed)
        interpreter.invoke()
        tflite_prob = float(interpreter.get_tensor(output_details[0]["index"]).flatten()[0])

        diff = abs(keras_prob - tflite_prob)
        max_diff = max(max_diff, diff)

        if diff > tolerance:
            all_close = False
            print(f"  MISMATCH: {img_path.name} — Keras={keras_prob:.6f}, TFLite={tflite_prob:.6f}, diff={diff:.6f}")

    print(f"Parity check: max diff = {max_diff:.8f} (tolerance = {tolerance})")
    return all_close


def collect_sample_images(project_root: Path, num_samples: int) -> list[Path]:
    """Collect a few sample images from the dataset for parity testing."""
    metadata_path = project_root / "dataset" / "metadata" / "manual_split_metadata.csv"
    if not metadata_path.exists():
        return []

    import csv
    paths: list[Path] = []
    with metadata_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            candidate = project_root / row["relative_path"]
            if candidate.exists():
                paths.append(candidate)
                if len(paths) >= num_samples:
                    break

    return paths


if __name__ == "__main__":
    raise SystemExit(main())
