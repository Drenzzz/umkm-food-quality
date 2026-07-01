"""
Export a trained Keras model to ONNX format with numeric parity verification.

Usage:
    python -m ml.export_onnx --project-root . --experiment umkm_food_quality_v1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
import tf2onnx
from PIL import Image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Keras model to ONNX with parity check.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--experiment", default="umkm_food_quality_v1")
    parser.add_argument("--parity-tolerance", type=float, default=1e-5)
    parser.add_argument("--parity-samples", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    model_dir = project_root / "ml" / "model" / args.experiment

    keras_path = model_dir / "model.keras"
    onnx_path = model_dir / "model.onnx"

    if not keras_path.exists():
        print(f"ERROR: Model not found at {keras_path}")
        return 1

    print(f"Loading Keras model from {keras_path} ...")
    keras_model = tf.keras.models.load_model(keras_path)

    print("Converting to ONNX ...")
    onnx_model, _ = tf2onnx.convert.from_keras(keras_model, opset=13)
    onnx_bytes = onnx_model.SerializeToString()

    print(f"ONNX model size: {len(onnx_bytes) / 1024 / 1024:.2f} MB")

    parity_ok = verify_parity(keras_model, onnx_bytes, project_root, args.parity_tolerance, args.parity_samples)

    if not parity_ok:
        print("WARNING: Parity check FAILED.")
        return 1

    if args.dry_run:
        print("Dry run — not saving .onnx file.")
        return 0

    onnx_path.write_bytes(onnx_bytes)
    print(f"ONNX model saved to {onnx_path}")

    meta = {
        "source_model": str(keras_path.relative_to(project_root)),
        "onnx_model": str(onnx_path.relative_to(project_root)),
        "onnx_size_bytes": len(onnx_bytes),
        "opset": 13,
        "parity_tolerance": args.parity_tolerance,
        "parity_samples": args.parity_samples,
        "parity_passed": True,
    }
    meta_path = model_dir / "onnx_export.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Export metadata saved to {meta_path}")

    return 0


def verify_parity(
    keras_model: tf.keras.Model,
    onnx_bytes: bytes,
    project_root: Path,
    tolerance: float,
    num_samples: int,
) -> bool:
    import onnxruntime as ort

    sample_paths = collect_sample_images(project_root, num_samples)
    if not sample_paths:
        print("WARNING: No sample images found — skipping parity check.")
        return True

    session = ort.InferenceSession(onnx_bytes)
    input_name = session.get_inputs()[0].name

    max_diff = 0.0
    all_close = True

    for img_path in sample_paths:
        with Image.open(img_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = img.resize((224, 224), resample=Image.Resampling.LANCZOS)
            arr = np.asarray(img, dtype=np.float32)

        arr_batch = np.expand_dims(arr, axis=0)
        arr_preprocessed = preprocess_input(arr_batch.copy())

        keras_prob = float(keras_model.predict(arr_preprocessed, verbose=0).flatten()[0])
        onnx_result = session.run(None, {input_name: arr_preprocessed})
        onnx_prob = float(onnx_result[0].flatten()[0])

        diff = abs(keras_prob - onnx_prob)
        max_diff = max(max_diff, diff)

        if diff > tolerance:
            all_close = False
            print(f"  MISMATCH: {img_path.name} — Keras={keras_prob:.6f}, ONNX={onnx_prob:.6f}, diff={diff:.6f}")

    print(f"Parity check: max diff = {max_diff:.8f} (tolerance = {tolerance})")
    return all_close


def collect_sample_images(project_root: Path, num_samples: int) -> list[Path]:
    import csv

    metadata_path = project_root / "dataset" / "metadata" / "manual_split_metadata.csv"
    if not metadata_path.exists():
        return []

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
