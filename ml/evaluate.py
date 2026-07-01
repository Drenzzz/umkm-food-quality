from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.artifacts import ensure_manifest, relative_to_model_dir, save_manifest, utc_now_iso


LABEL_TO_INDEX = {
    "layak_jual": 0,
    "tidak_layak_jual": 1,
}
INDEX_TO_LABEL = {value: key for key, value in LABEL_TO_INDEX.items()}


@dataclass(frozen=True)
class EvaluationRow:
    image_id: str
    image_path: Path
    final_label: str
    split: str
    dataset_slug: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate baseline model metrics with recall priority.")
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
        help="Batch size for evaluation dataset.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold for the sigmoid output.",
    )
    parser.add_argument(
        "--tta",
        action="store_true",
        help="Enable Test-Time Augmentation: average predictions over flipped variants.",
    )
    parser.add_argument(
        "--split-name",
        default="test",
        choices=["train", "val", "test"],
        help="Preferred split for evaluation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview selected evaluation rows without running model inference.",
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
    evaluation_rows, used_split = select_evaluation_rows(rows, args.split_name)

    print(f"Experiment: {args.experiment}")
    print(f"Requested split: {args.split_name}")
    print(f"Used split: {used_split}")
    print(f"Evaluation samples: {len(evaluation_rows)}")
    print(f"Threshold: {args.threshold}")

    if args.dry_run:
        return 0

    model = tf.keras.models.load_model(model_dir / "model.keras")
    dataset = build_dataset(evaluation_rows, args.image_size, args.batch_size)

    y_true = np.array([LABEL_TO_INDEX[row.final_label] for row in evaluation_rows], dtype=np.int32)

    if args.tta:
        y_prob = predict_with_tta(model, evaluation_rows, args.image_size)
    else:
        y_prob = model.predict(dataset, verbose=0).flatten()

    y_pred = (y_prob >= args.threshold).astype(np.int32)

    metrics = compute_metrics(y_true, y_pred)
    report = classification_report(
        y_true,
        y_pred,
        target_names=[INDEX_TO_LABEL[0], INDEX_TO_LABEL[1]],
        output_dict=True,
        zero_division=0,
    )

    save_confusion_matrix(output_dir / "confusion_matrix.png", y_true, y_pred)
    save_evaluation_report(
        output_dir / "evaluation_report.json",
        args.experiment,
        used_split,
        args.threshold,
        metrics,
        report,
        y_true,
        y_pred,
    )
    manifest.files.update(
        {
            "evaluation_report": relative_to_model_dir(model_dir, output_dir / "evaluation_report.json"),
            "confusion_matrix": relative_to_model_dir(model_dir, output_dir / "confusion_matrix.png"),
        }
    )
    manifest.evaluation = {
        "used_split": used_split,
        "threshold": args.threshold,
        "sample_count": int(len(y_true)),
        "priority_metric": "recall_tidak_layak_jual",
        "finished_at": utc_now_iso(),
    }
    save_manifest(model_dir, manifest)

    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision_macro']:.4f}")
    print(f"Recall: {metrics['recall_macro']:.4f}")
    print(f"F1: {metrics['f1_macro']:.4f}")
    print(f"Recall Tidak Layak Jual: {metrics['recall_tidak_layak_jual']:.4f}")
    print(f"Report path: {output_dir / 'evaluation_report.json'}")
    print(f"Confusion matrix path: {output_dir / 'confusion_matrix.png'}")
    return 0


def load_rows(split_csv: Path, project_root: Path, experiment_name: str) -> list[EvaluationRow]:
    experiment_path = project_root / "ml" / "experiments" / f"{experiment_name}.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    scope = experiment["dataset_scope"]
    dataset_slugs = set(scope["dataset_slugs"])
    product_domains = set(scope["product_domains"])
    allowed_labels = set(scope["allowed_labels"])

    rows: list[EvaluationRow] = []
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
                EvaluationRow(
                    image_id=row["image_id"],
                    image_path=project_root / row["relative_path"],
                    final_label=row["final_label"],
                    split=row["split"],
                    dataset_slug=row["dataset_slug"],
                )
            )
    if not rows:
        raise ValueError("No evaluation rows matched the selected experiment scope.")
    return rows


def select_evaluation_rows(rows: list[EvaluationRow], preferred_split: str) -> tuple[list[EvaluationRow], str]:
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
    raise ValueError("No rows available for evaluation.")


def build_dataset(rows: list[EvaluationRow], image_size: int, batch_size: int) -> tf.data.Dataset:
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


def predict_with_tta(
    model: tf.keras.Model,
    rows: list[EvaluationRow],
    image_size: int,
    batch_size: int = 32,
) -> np.ndarray:
    """Average sigmoid predictions over the original image and horizontal flip."""
    path_tensor = tf.constant([str(r.image_path) for r in rows])
    label_tensor = tf.constant([0.0] * len(rows), dtype=tf.float32)

    ds = tf.data.Dataset.from_tensor_slices((path_tensor, label_tensor))
    ds = ds.map(
        lambda p, l: load_and_preprocess_image(p, l, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    probs_original = model.predict(ds, verbose=0).flatten()

    ds_flipped = tf.data.Dataset.from_tensor_slices((path_tensor, label_tensor))
    ds_flipped = ds_flipped.map(
        lambda p, l: _load_image_flipped(p, l, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    ds_flipped = ds_flipped.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    probs_flipped = model.predict(ds_flipped, verbose=0).flatten()

    return (probs_original + probs_flipped) / 2.0


def _load_image_flipped(path: tf.Tensor, label: tf.Tensor, size: int) -> tuple[tf.Tensor, tf.Tensor]:
    raw = tf.io.read_file(path)
    img = tf.image.decode_jpeg(raw, channels=3)
    img = tf.image.resize(img, [size, size])
    img = tf.image.flip_left_right(img)
    img = preprocess_input(tf.cast(img, tf.float32))
    return img, label


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    accuracy = float(np.mean(y_true == y_pred))
    precision_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    recall_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

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
        "accuracy": accuracy,
        "precision_macro": precision_macro,
        "recall_macro": recall_macro,
        "f1_macro": f1_macro,
        "recall_tidak_layak_jual": recall_tidak_layak,
    }


def save_confusion_matrix(output_path: Path, y_true: np.ndarray, y_pred: np.ndarray) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=[INDEX_TO_LABEL[0], INDEX_TO_LABEL[1]])
    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(values_format="d", ax=ax, colorbar=False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def save_evaluation_report(
    output_path: Path,
    experiment_name: str,
    used_split: str,
    threshold: float,
    metrics: dict[str, float],
    report: dict[str, object],
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> None:
    payload = {
        "experiment": experiment_name,
        "used_split": used_split,
        "threshold": threshold,
        "sample_count": int(len(y_true)),
        "metrics": metrics,
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
