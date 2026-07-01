"""
Stratified K-Fold cross-validation for MobileNetV2.

Reports mean ± std across folds for accuracy, precision, recall, F1.
Requires GPU for practical training times.

Usage:
    python -m ml.cross_validate --project-root .
    python -m ml.cross_validate --project-root . --folds 5 --feature-epochs 10 --finetune-epochs 4
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.model_selection import StratifiedKFold
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.callbacks import CSVLogger, EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.train import (
    SampleRow,
    build_class_weight,
    load_experiment_rows,
    unfreeze_backbone,
)

LABEL_TO_INDEX = {"layak_jual": 0, "tidak_layak_jual": 1}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="K-fold cross-validation for MobileNetV2.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--experiment", default="umkm_food_quality_v1")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--feature-epochs", type=int, default=10)
    parser.add_argument("--finetune-epochs", type=int, default=4)
    parser.add_argument("--finetune-layers", type=int, default=40)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def build_model(image_size: int) -> tuple[tf.keras.Model, tf.keras.Model]:
    backbone = MobileNetV2(
        input_shape=(image_size, image_size, 3),
        include_top=False,
        weights="imagenet",
    )
    backbone.trainable = False

    x = GlobalAveragePooling2D()(backbone.output)
    x = Dropout(0.4)(x)
    x = Dense(128, activation="relu")(x)
    x = Dropout(0.2)(x)
    output = Dense(1, activation="sigmoid")(x)
    model = tf.keras.Model(inputs=backbone.input, outputs=output)
    return model, backbone


def compile_model(model: tf.keras.Model, lr: float) -> None:
    model.compile(
        optimizer=Adam(learning_rate=lr),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )


def build_fold_dataset(rows: list[SampleRow], image_size: int, batch_size: int) -> tf.data.Dataset:
    path_tensor = tf.constant([str(r.image_path) for r in rows])
    label_tensor = tf.constant([LABEL_TO_INDEX[r.final_label] for r in rows], dtype=tf.float32)
    ds = tf.data.Dataset.from_tensor_slices((path_tensor, label_tensor))
    ds = ds.map(
        lambda p, l: _load_image(p, l, image_size),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds


def _load_image(path: tf.Tensor, label: tf.Tensor, size: int) -> tuple[tf.Tensor, tf.Tensor]:
    raw = tf.io.read_file(path)
    img = tf.image.decode_jpeg(raw, channels=3)
    img = tf.image.resize(img, [size, size])
    img = preprocess_input(tf.cast(img, tf.float32))
    return img, label


def evaluate_fold(model: tf.keras.Model, rows: list[SampleRow], image_size: int, threshold: float) -> dict[str, float]:
    ds = build_fold_dataset(rows, image_size, batch_size=32)
    probs = model.predict(ds, verbose=0).flatten()
    labels = np.array([LABEL_TO_INDEX[r.final_label] for r in rows], dtype=np.int32)
    preds = (probs >= threshold).astype(np.int32)

    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    return {
        "accuracy": float(accuracy_score(labels, preds)),
        "precision_macro": float(precision_score(labels, preds, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(labels, preds, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(labels, preds, average="macro", zero_division=0)),
        "recall_tidak_layak_jual": float(
            recall_score(labels, preds, labels=[1], average=None, zero_division=0)[0]
        ),
    }


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    metadata_path = project_root / "dataset" / "metadata" / "manual_split_metadata.csv"
    output_dir = args.output_dir or project_root / "ml" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_experiment_rows(metadata_path, project_root, _load_experiment(project_root, args.experiment))
    print(f"Total samples: {len(rows)}")
    print(f"Folds: {args.folds}")

    labels = np.array([LABEL_TO_INDEX[r.final_label] for r in rows], dtype=np.int32)
    skf = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=42)

    fold_metrics: list[dict[str, float]] = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(rows, labels)):
        print(f"\n{'='*50}")
        print(f"Fold {fold_idx + 1}/{args.folds}")
        print(f"  Train: {len(train_idx)}, Val: {len(val_idx)}")

        train_rows = [rows[i] for i in train_idx]
        val_rows = [rows[i] for i in val_idx]

        class_weight = build_class_weight(train_rows)
        train_ds = build_fold_dataset(train_rows, args.image_size, args.batch_size)
        val_ds = build_fold_dataset(val_rows, args.image_size, args.batch_size)

        model, backbone = build_model(args.image_size)

        # Phase 1: feature extraction
        compile_model(model, lr=1e-3)
        model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=args.feature_epochs,
            class_weight=class_weight,
            callbacks=[
                EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
                ReduceLROnPlateau(monitor="val_loss", patience=2, factor=0.5, min_lr=1e-7),
            ],
            verbose=0,
        )

        # Phase 2: fine-tuning
        unfreeze_backbone(backbone, args.finetune_layers)
        compile_model(model, lr=1e-5)
        model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=args.finetune_epochs,
            class_weight=class_weight,
            callbacks=[
                EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
            ],
            verbose=0,
        )

        threshold = 0.3
        metrics = evaluate_fold(model, val_rows, args.image_size, threshold)
        fold_metrics.append(metrics)

        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  Recall (tidak_layak): {metrics['recall_tidak_layak_jual']:.4f}")
        print(f"  F1: {metrics['f1_macro']:.4f}")

        # Free memory between folds
        del model, backbone
        tf.keras.backend.clear_session()

    # Aggregate
    agg = {}
    for key in fold_metrics[0]:
        values = [m[key] for m in fold_metrics]
        agg[key] = {
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
            "min": round(float(np.min(values)), 4),
            "max": round(float(np.max(values)), 4),
            "per_fold": [round(v, 4) for v in values],
        }

    result = {
        "experiment": args.experiment,
        "folds": args.folds,
        "threshold": 0.3,
        "total_samples": len(rows),
        "aggregated_metrics": agg,
    }

    report_path = output_dir / "kfold_cv_report.json"
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*50}")
    print("K-FOLD CROSS-VALIDATION RESULTS")
    print(f"{'='*50}")
    for key, stats in agg.items():
        print(f"  {key}: {stats['mean']:.4f} ± {stats['std']:.4f}")
    print(f"\nReport saved to: {report_path}")

    return 0


def _load_experiment(project_root: Path, experiment_id: str) -> dict:
    path = project_root / "ml" / "experiments" / f"{experiment_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
