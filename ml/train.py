from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.callbacks import CSVLogger, EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
from tensorflow.keras.metrics import Precision, Recall
from tensorflow.keras.optimizers import Adam

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.artifacts import ensure_manifest, relative_to_model_dir, save_manifest, utc_now_iso


LABEL_TO_INDEX = {
    "layak_jual": 0,
    "tidak_layak_jual": 1,
}


@dataclass(frozen=True)
class SampleRow:
    image_id: str
    image_path: Path
    final_label: str
    split: str
    dataset_slug: str
    product_domain: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a MobileNetV2 baseline from experiment definitions.")
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
        "--image-size",
        type=int,
        default=224,
        help="Square image size for model input.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for tf.data datasets.",
    )
    parser.add_argument(
        "--feature-epochs",
        type=int,
        default=10,
        help="Epochs for frozen backbone training.",
    )
    parser.add_argument(
        "--finetune-epochs",
        type=int,
        default=10,
        help="Epochs for fine-tuning stage.",
    )
    parser.add_argument(
        "--finetune-layers",
        type=int,
        default=40,
        help="Number of tail layers to unfreeze for fine-tuning.",
    )
    parser.add_argument(
        "--weights",
        default="imagenet",
        choices=["imagenet", "none"],
        help="Backbone weights used for MobileNetV2.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory for training artifacts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load experiment data and build model without training.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    experiment_path = project_root / "ml" / "experiments" / f"{args.experiment}.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    metadata_path = project_root / experiment["training_plan"]["split_metadata"]
    output_dir = args.output_dir.resolve() if args.output_dir else project_root / "ml" / "model" / args.experiment
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = ensure_manifest(output_dir, experiment["experiment_id"], experiment["training_plan"]["model_family"])

    rows = load_experiment_rows(metadata_path, project_root, experiment)
    split_rows = prepare_splits(rows)
    train_ds = build_dataset(split_rows["train"], args.image_size, args.batch_size, training=True)
    val_ds = build_dataset(split_rows["val"], args.image_size, args.batch_size, training=False)
    class_weight = build_class_weight(split_rows["train"])

    model, backbone = build_model(args.image_size, args.weights)

    print(f"Experiment: {experiment['experiment_id']}")
    print(f"Train samples: {len(split_rows['train'])}")
    print(f"Validation samples: {len(split_rows['val'])}")
    print(f"Train class weight: {class_weight}")
    print(f"Weights: {args.weights}")
    print(f"Output dir: {output_dir}")

    if args.dry_run:
        model.summary(print_fn=lambda line: print(line))
        return 0

    callbacks = [
        CSVLogger(output_dir / "training_log.csv"),
        EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", patience=2, factor=0.5, min_lr=1e-7),
    ]

    compile_model(model, learning_rate=1e-3)
    feature_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.feature_epochs,
        callbacks=callbacks,
        class_weight=class_weight,
        verbose=2,
    )

    unfreeze_backbone(backbone, args.finetune_layers)
    compile_model(model, learning_rate=1e-5)
    finetune_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.finetune_epochs,
        callbacks=callbacks,
        class_weight=class_weight,
        verbose=2,
    )

    validation_probs = model.predict(val_ds, verbose=0).flatten()
    assert_model_quality(split_rows["val"], validation_probs, 0.5)

    model.save(output_dir / "model.keras")
    (output_dir / "class_indices.json").write_text(json.dumps(LABEL_TO_INDEX, indent=2), encoding="utf-8")
    (output_dir / "training_history.json").write_text(
        json.dumps(
            {
                "feature_extraction": feature_history.history,
                "fine_tuning": finetune_history.history,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest.status = "trained"
    manifest.files.update(
        {
            "model": relative_to_model_dir(output_dir, output_dir / "model.keras"),
            "class_indices": relative_to_model_dir(output_dir, output_dir / "class_indices.json"),
            "training_history": relative_to_model_dir(output_dir, output_dir / "training_history.json"),
            "training_log": relative_to_model_dir(output_dir, output_dir / "training_log.csv"),
        }
    )
    manifest.training = {
        "split_metadata": str(metadata_path.relative_to(project_root)).replace("\\", "/"),
        "feature_epochs": args.feature_epochs,
        "finetune_epochs": args.finetune_epochs,
        "finetune_layers": args.finetune_layers,
        "weights": args.weights,
        "image_size": args.image_size,
        "batch_size": args.batch_size,
        "finished_at": utc_now_iso(),
    }
    save_manifest(output_dir, manifest)
    print("Training completed.")
    return 0


def load_experiment_rows(metadata_path: Path, project_root: Path, experiment: dict[str, object]) -> list[SampleRow]:
    scope = experiment["dataset_scope"]
    dataset_slugs = set(scope["dataset_slugs"])
    product_domains = set(scope["product_domains"])
    allowed_labels = set(scope["allowed_labels"])

    rows: list[SampleRow] = []
    with metadata_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["dataset_slug"] not in dataset_slugs:
                continue
            if row["product_domain"] not in product_domains:
                continue
            if row["final_label"] not in allowed_labels:
                continue
            rows.append(
                SampleRow(
                    image_id=row["image_id"],
                    image_path=project_root / row["relative_path"],
                    final_label=row["final_label"],
                    split=row["split"],
                    dataset_slug=row["dataset_slug"],
                    product_domain=row["product_domain"],
                )
            )
    if not rows:
        raise ValueError("No samples matched the selected experiment scope.")
    return rows


def prepare_splits(rows: list[SampleRow]) -> dict[str, list[SampleRow]]:
    grouped = {
        "train": [row for row in rows if row.split == "train"],
        "val": [row for row in rows if row.split == "val"],
        "test": [row for row in rows if row.split == "test"],
    }

    if not grouped["train"]:
        raise ValueError("Training split is empty for the selected experiment.")

    if not grouped["val"]:
        fallback_train, fallback_val = fallback_validation_split(grouped["train"])
        grouped["train"] = fallback_train
        grouped["val"] = fallback_val

    validate_split_label_coverage(grouped)

    return grouped


def fallback_validation_split(train_rows: list[SampleRow]) -> tuple[list[SampleRow], list[SampleRow]]:
    if len(train_rows) < 2:
        raise ValueError("At least two training samples are required to create a validation fallback split.")

    grouped_by_label: dict[str, list[SampleRow]] = {
        "layak_jual": [],
        "tidak_layak_jual": [],
    }
    for row in train_rows:
        grouped_by_label[row.final_label].append(row)

    fallback_val: list[SampleRow] = []
    fallback_train: list[SampleRow] = []
    for label_name, label_rows in grouped_by_label.items():
        if len(label_rows) == 1:
            fallback_val.append(label_rows[0])
            continue
        fallback_val.append(label_rows[-1])
        fallback_train.extend(label_rows[:-1])

    if not fallback_train:
        fallback_train = train_rows[:-1]
        fallback_val = train_rows[-1:]

    if not fallback_val:
        raise ValueError("Validation fallback split could not be created.")

    return fallback_train, fallback_val


def build_dataset(rows: list[SampleRow], image_size: int, batch_size: int, training: bool) -> tf.data.Dataset:
    path_tensor = tf.constant([str(row.image_path) for row in rows])
    label_tensor = tf.constant([LABEL_TO_INDEX[row.final_label] for row in rows], dtype=tf.float32)
    dataset = tf.data.Dataset.from_tensor_slices((path_tensor, label_tensor))

    if training:
        dataset = dataset.shuffle(buffer_size=max(len(rows), 1), reshuffle_each_iteration=True)

    dataset = dataset.map(
        lambda image_path, label: load_and_preprocess_image(image_path, label, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    if training:
        dataset = dataset.map(
            lambda image, label: (augment_image(image), label),
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


def build_class_weight(train_rows: list[SampleRow]) -> dict[int, float]:
    counts = Counter(LABEL_TO_INDEX[row.final_label] for row in train_rows)
    total = sum(counts.values())
    class_weight: dict[int, float] = {}
    for label_index in sorted(LABEL_TO_INDEX.values()):
        count = counts.get(label_index, 0)
        if count == 0:
            raise ValueError(f"Training split is missing class index {label_index}")
        class_weight[label_index] = round(total / (len(LABEL_TO_INDEX) * count), 6)
    return class_weight


def validate_split_label_coverage(grouped: dict[str, list[SampleRow]]) -> None:
    train_labels = {row.final_label for row in grouped["train"]}
    val_labels = {row.final_label for row in grouped["val"]}
    missing_in_train = set(LABEL_TO_INDEX) - train_labels
    if missing_in_train:
        raise ValueError(f"Training split is missing labels: {sorted(missing_in_train)}")

    missing_in_val = set(LABEL_TO_INDEX) - val_labels
    if missing_in_val:
        raise ValueError(f"Validation split is missing labels: {sorted(missing_in_val)}")


def augment_image(image: tf.Tensor) -> tf.Tensor:
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_flip_up_down(image)
    image = tf.image.random_brightness(image, max_delta=0.15)
    image = tf.image.random_contrast(image, lower=0.9, upper=1.1)
    image = tf.image.random_hue(image, max_delta=0.05)
    image = tf.image.random_saturation(image, lower=0.9, upper=1.1)
    return tf.clip_by_value(image, -1.0, 1.0)


def assert_model_quality(validation_rows: list[SampleRow], probabilities: np.ndarray, threshold: float) -> None:
    labels = np.array([LABEL_TO_INDEX[row.final_label] for row in validation_rows], dtype=np.int32)
    predictions = (probabilities >= threshold).astype(np.int32)
    unique_scores = len({round(float(score), 6) for score in probabilities.tolist()})
    predicted_counts = Counter(int(prediction) for prediction in predictions.tolist())
    dominant_share = max(predicted_counts.values()) / len(predictions)
    recall_by_label = compute_recall_by_label(labels, predictions)

    failures: list[str] = []
    if unique_scores <= 1:
        failures.append("constant_raw_score")
    if dominant_share >= 0.95:
        failures.append("single_class_prediction_dominance")
    for label_name, recall in recall_by_label.items():
        if recall == 0:
            failures.append(f"zero_recall_{label_name}")

    if failures:
        raise RuntimeError(f"Training quality gate failed: {', '.join(failures)}")


def compute_recall_by_label(labels: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    scores: dict[str, float] = {}
    for label_name, label_index in LABEL_TO_INDEX.items():
        mask = labels == label_index
        total = int(mask.sum())
        if total == 0:
            scores[label_name] = 0.0
            continue
        correct = int((predictions[mask] == label_index).sum())
        scores[label_name] = round(correct / total, 6)
    return scores


def build_model(image_size: int, weights: str) -> tuple[Model, Model]:
    backbone_weights = None if weights == "none" else weights
    backbone = MobileNetV2(
        input_shape=(image_size, image_size, 3),
        include_top=False,
        weights=backbone_weights,
    )
    backbone.trainable = False

    x = GlobalAveragePooling2D()(backbone.output)
    x = Dropout(0.4)(x)
    x = Dense(128, activation="relu")(x)
    x = Dropout(0.2)(x)
    output = Dense(1, activation="sigmoid")(x)
    model = Model(inputs=backbone.input, outputs=output)
    return model, backbone


def compile_model(model: Model, learning_rate: float) -> None:
    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=["accuracy", Precision(name="precision"), Recall(name="recall")],
    )


def unfreeze_backbone(backbone: Model, finetune_layers: int) -> None:
    backbone.trainable = True
    if finetune_layers <= 0:
        return
    for layer in backbone.layers[:-finetune_layers]:
        layer.trainable = False


if __name__ == "__main__":
    raise SystemExit(main())
