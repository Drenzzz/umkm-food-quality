from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

from ml.artifacts import ensure_manifest, relative_to_model_dir, save_manifest, utc_now_iso


LABEL_TO_INDEX = {
    "layak_jual": 0,
    "tidak_layak_jual": 1,
}


@dataclass(frozen=True)
class ThresholdRow:
    image_id: str
    image_path: Path
    final_label: str
    split: str
    dataset_slug: str
    product_domain: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review sigmoid thresholds with recall priority.")
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
    parser.add_argument(
        "--split-csv",
        type=Path,
        default=None,
        help="Optional split metadata CSV path.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=None,
        help="Optional trained model directory path.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=224,
        help="Square image size used by the model.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for threshold evaluation dataset.",
    )
    parser.add_argument(
        "--split-name",
        default="val",
        choices=["train", "val", "test"],
        help="Preferred split for threshold review.",
    )
    parser.add_argument(
        "--threshold-start",
        type=float,
        default=0.1,
        help="Starting threshold value.",
    )
    parser.add_argument(
        "--threshold-stop",
        type=float,
        default=0.9,
        help="Final threshold value.",
    )
    parser.add_argument(
        "--threshold-step",
        type=float,
        default=0.1,
        help="Step size for threshold sweep.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview selected rows without running prediction.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    split_csv = args.split_csv.resolve() if args.split_csv else project_root / "dataset" / "metadata" / "split_metadata.csv"
    model_dir = args.model_dir.resolve() if args.model_dir else project_root / "ml" / "model" / args.experiment
    output_dir = model_dir / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = ensure_manifest(model_dir, args.experiment, "MobileNetV2")

    rows = load_rows(split_csv, project_root, args.experiment)
    selected_rows, used_split = select_rows(rows, args.split_name)

    print(f"Experiment: {args.experiment}")
    print(f"Requested split: {args.split_name}")
    print(f"Used split: {used_split}")
    print(f"Sample count: {len(selected_rows)}")

    if args.dry_run:
        return 0

    model = tf.keras.models.load_model(model_dir / "model.keras")
    dataset = build_dataset(selected_rows, args.image_size, args.batch_size)
    y_true = np.array([LABEL_TO_INDEX[row.final_label] for row in selected_rows], dtype=np.int32)
    y_prob = model.predict(dataset, verbose=0).flatten()

    threshold_results = []
    for threshold in generate_thresholds(args.threshold_start, args.threshold_stop, args.threshold_step):
        y_pred = (y_prob >= threshold).astype(np.int32)
        threshold_results.append(compute_threshold_metrics(threshold, y_true, y_pred))

    best_threshold = select_best_threshold(threshold_results)
    report = {
        "experiment": args.experiment,
        "used_split": used_split,
        "priority_metric": "recall_tidak_layak_jual",
        "thresholds": threshold_results,
        "recommended_threshold": best_threshold,
    }

    output_path = output_dir / "threshold_review.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest.files["threshold_review"] = relative_to_model_dir(model_dir, output_path)
    manifest.threshold_review = {
        "used_split": used_split,
        "priority_metric": "recall_tidak_layak_jual",
        "recommended_threshold": best_threshold["threshold"],
        "threshold_count": len(threshold_results),
        "finished_at": utc_now_iso(),
    }
    save_manifest(model_dir, manifest)

    print(f"Recommended threshold: {best_threshold['threshold']:.2f}")
    print(f"Recall Tidak Layak Jual: {best_threshold['recall_tidak_layak_jual']:.4f}")
    print(f"Precision Macro: {best_threshold['precision_macro']:.4f}")
    print(f"F1 Macro: {best_threshold['f1_macro']:.4f}")
    print(f"Report path: {output_path}")
    return 0


def load_rows(split_csv: Path, project_root: Path, experiment_name: str) -> list[ThresholdRow]:
    experiment_path = project_root / "ml" / "experiments" / f"{experiment_name}.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    scope = experiment["dataset_scope"]
    dataset_slugs = set(scope["dataset_slugs"])
    product_domains = set(scope["product_domains"])
    allowed_labels = set(scope["allowed_labels"])

    rows: list[ThresholdRow] = []
    with split_csv.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["dataset_slug"] not in dataset_slugs:
                continue
            if row["product_domain"] not in product_domains:
                continue
            if row["final_label"] not in allowed_labels:
                continue
            rows.append(
                ThresholdRow(
                    image_id=row["image_id"],
                    image_path=project_root / row["relative_path"],
                    final_label=row["final_label"],
                    split=row["split"],
                    dataset_slug=row["dataset_slug"],
                    product_domain=row["product_domain"],
                )
            )
    if not rows:
        raise ValueError("No rows matched the selected experiment scope.")
    return rows


def select_rows(rows: list[ThresholdRow], preferred_split: str) -> tuple[list[ThresholdRow], str]:
    grouped = {
        "train": [row for row in rows if row.split == "train"],
        "val": [row for row in rows if row.split == "val"],
        "test": [row for row in rows if row.split == "test"],
    }
    if grouped[preferred_split]:
        return grouped[preferred_split], preferred_split
    if grouped["val"]:
        return grouped["val"], "val"
    if grouped["train"]:
        return grouped["train"], "train"
    raise ValueError("No rows available for threshold review.")


def build_dataset(rows: list[ThresholdRow], image_size: int, batch_size: int) -> tf.data.Dataset:
    path_tensor = tf.constant([str(row.image_path) for row in rows])
    label_tensor = tf.constant([LABEL_TO_INDEX[row.final_label] for row in rows], dtype=tf.float32)
    dataset = tf.data.Dataset.from_tensor_slices((path_tensor, label_tensor))
    dataset = dataset.map(
        lambda image_path, label: load_and_preprocess_image(image_path, label, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    dataset = dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return dataset


def load_and_preprocess_image(image_path: tf.Tensor, label: tf.Tensor, image_size: int) -> tuple[tf.Tensor, tf.Tensor]:
    image_bytes = tf.io.read_file(image_path)
    image = tf.image.decode_jpeg(image_bytes, channels=3)
    image = tf.image.resize(image, [image_size, image_size])
    image = preprocess_input(tf.cast(image, tf.float32))
    return image, label


def generate_thresholds(start: float, stop: float, step: float) -> list[float]:
    values = np.arange(start, stop + 1e-8, step, dtype=np.float32)
    return [round(float(value), 4) for value in values]


def compute_threshold_metrics(threshold: float, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    recall_tidak_layak = float(
        recall_score(
            y_true,
            y_pred,
            labels=[LABEL_TO_INDEX["tidak_layak_jual"]],
            average=None,
            zero_division=0,
        )[0]
    )
    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_tidak_layak_jual": recall_tidak_layak,
    }


def select_best_threshold(results: list[dict[str, float]]) -> dict[str, float]:
    return sorted(
        results,
        key=lambda item: (
            item["recall_tidak_layak_jual"],
            item["f1_macro"],
            item["precision_macro"],
            -abs(item["threshold"] - 0.5),
        ),
        reverse=True,
    )[0]


if __name__ == "__main__":
    raise SystemExit(main())
