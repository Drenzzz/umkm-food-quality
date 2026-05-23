from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
from PIL import Image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ModelArtifact:
    experiment_id: str
    model_path: Path
    class_indices_path: Path
    threshold: float


@dataclass(frozen=True)
class ImageSample:
    image_id: str
    image_path: Path
    expected_label: str
    split: str
    dataset_slug: str
    product_domain: str


@dataclass(frozen=True)
class PredictionOutput:
    model_id: str
    image_id: str
    image_path: str
    expected_label: str
    predicted_label: str
    raw_score: float
    threshold: float
    confidence_score: float
    split: str
    dataset_slug: str
    product_domain: str


@dataclass(frozen=True)
class ModelQualitySummary:
    model_id: str
    sample_count: int
    raw_score_min: float
    raw_score_max: float
    raw_score_unique_count: int
    predicted_label_counts: dict[str, int]
    expected_label_counts: dict[str, int]
    recall_by_label: dict[str, float]
    dominant_prediction_share: float
    collapse_flags: list[str]
    passed_quality_gate: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate raw prediction outputs for registered model artifacts.")
    parser.add_argument("--metadata", default="dataset/metadata/split_metadata.csv", help="CSV metadata path.")
    parser.add_argument("--model-root", default="ml/model", help="Model registry root directory.")
    parser.add_argument("--active-config", default="ml/model/active_model.json", help="Active model config path.")
    parser.add_argument("--split", default="test", help="Dataset split to evaluate.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of images to evaluate.")
    parser.add_argument("--model-id", default="all", help="Model experiment id to evaluate, or 'all'.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    parser.add_argument("--quality-report", default="", help="Optional model quality report JSON path.")
    parser.add_argument("--domain-bias-report", default="", help="Optional domain bias report JSON path.")
    return parser.parse_args()


def load_samples(metadata_path: Path, split: str, limit: int) -> list[ImageSample]:
    path = metadata_path if metadata_path.is_absolute() else PROJECT_ROOT / metadata_path
    samples: list[ImageSample] = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("split") != split:
                continue

            image_path = PROJECT_ROOT / str(row["relative_path"])
            if not image_path.exists():
                continue

            samples.append(
                ImageSample(
                    image_id=str(row["image_id"]),
                    image_path=image_path,
                    expected_label=str(row["final_label"]),
                    split=str(row["split"]),
                    dataset_slug=str(row["dataset_slug"]),
                    product_domain=str(row["product_domain"]),
                )
            )

    if len(samples) <= limit:
        return samples

    return select_stratified_samples(samples, limit)


def select_stratified_samples(samples: list[ImageSample], limit: int) -> list[ImageSample]:
    grouped: dict[str, list[ImageSample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.product_domain].append(sample)

    selected: list[ImageSample] = []
    total = len(samples)
    for product_domain in sorted(grouped):
        domain_samples = grouped[product_domain]
        allocation = max(1, round(limit * len(domain_samples) / total))
        selected.extend(domain_samples[: min(allocation, len(domain_samples))])

    if len(selected) < limit:
        selected_ids = {sample.image_id for sample in selected}
        for sample in samples:
            if sample.image_id in selected_ids:
                continue
            selected.append(sample)
            if len(selected) >= limit:
                break

    return selected[:limit]


def select_models(model_id: str, model_root: Path, active_config_path: Path) -> list[ModelArtifact]:
    registry = discover_model_artifacts(model_root, active_config_path)
    if model_id == "all":
        return registry

    models = [model for model in registry if model.experiment_id == model_id]
    if not models:
        raise ValueError(f"Model '{model_id}' was not found in the registry")
    return models


def discover_model_artifacts(model_root: Path, active_config_path: Path) -> list[ModelArtifact]:
    root = PROJECT_ROOT / model_root
    active_config = load_json(PROJECT_ROOT / active_config_path)
    active_model_path = active_config.get("model_path")
    models: list[ModelArtifact] = []
    for model_dir in sorted(root.glob("exp_*")):
        manifest = load_json(model_dir / "artifact_manifest.json")
        experiment_id = str(manifest.get("experiment_id", model_dir.name))
        models.append(
            ModelArtifact(
                experiment_id=experiment_id,
                model_path=model_dir / "model.keras",
                class_indices_path=model_dir / "class_indices.json",
                threshold=load_threshold(model_dir, manifest),
            )
        )

    if active_model_path and not any(model.model_path == PROJECT_ROOT / str(active_model_path) for model in models):
        raise ValueError("Active model config points to an unknown model artifact")
    return models


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_threshold(model_dir: Path, manifest: dict[str, Any]) -> float:
    review = manifest.get("threshold_review")
    if isinstance(review, dict) and "recommended_threshold" in review:
        return float(review["recommended_threshold"])

    threshold_path = model_dir / "evaluation" / "threshold_review.json"
    if threshold_path.exists():
        payload = load_json(threshold_path)
        recommended = payload.get("recommended_threshold")
        if isinstance(recommended, dict) and "threshold" in recommended:
            return float(recommended["threshold"])
        if isinstance(recommended, int | float):
            return float(recommended)

    evaluation = manifest.get("evaluation")
    if isinstance(evaluation, dict) and "threshold" in evaluation:
        return float(evaluation["threshold"])
    return 0.5


def load_class_indices(model: ModelArtifact) -> dict[str, int]:
    payload = json.loads(model.class_indices_path.read_text(encoding="utf-8"))
    return {str(key): int(value) for key, value in payload.items()}


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        image = image.resize((224, 224), resample=Image.Resampling.LANCZOS)
        array = np.asarray(image, dtype=np.float32)
    array = np.expand_dims(array, axis=0)
    return preprocess_input(array)


def predict_sample(model: ModelArtifact, keras_model: tf.keras.Model, class_indices: dict[str, int], sample: ImageSample) -> PredictionOutput:
    tensor = preprocess_image(sample.image_path.read_bytes())
    raw_score = float(keras_model.predict(tensor, verbose=0).flatten()[0])
    index_to_label = {index: key for key, index in class_indices.items()}
    predicted_index = 1 if raw_score >= model.threshold else 0
    predicted_label = index_to_label[predicted_index]
    confidence = raw_score if predicted_index == 1 else 1 - raw_score
    return PredictionOutput(
        model_id=model.experiment_id,
        image_id=sample.image_id,
        image_path=str(sample.image_path),
        expected_label=sample.expected_label,
        predicted_label=predicted_label,
        raw_score=round(raw_score, 6),
        threshold=model.threshold,
        confidence_score=round(confidence * 100, 2),
        split=sample.split,
        dataset_slug=sample.dataset_slug,
        product_domain=sample.product_domain,
    )


def evaluate_models(models: list[ModelArtifact], samples: list[ImageSample]) -> list[PredictionOutput]:
    outputs: list[PredictionOutput] = []
    for model in models:
        keras_model = tf.keras.models.load_model(model.model_path)
        class_indices = load_class_indices(model)
        for sample in samples:
            outputs.append(predict_sample(model, keras_model, class_indices, sample))
    return outputs


def build_payload(outputs: list[PredictionOutput]) -> dict[str, Any]:
    return {
        "total_outputs": len(outputs),
        "outputs": [asdict(output) for output in outputs],
    }


def build_quality_report(outputs: list[PredictionOutput]) -> dict[str, Any]:
    grouped: dict[str, list[PredictionOutput]] = defaultdict(list)
    for output in outputs:
        grouped[output.model_id].append(output)

    summaries = [build_quality_summary(model_id, model_outputs) for model_id, model_outputs in sorted(grouped.items())]
    return {
        "quality_gate": {
            "raw_score_unique_minimum": 2,
            "dominant_prediction_share_maximum": 0.95,
            "required_recall_labels": ["layak_jual", "tidak_layak_jual"],
        },
        "models": [asdict(summary) for summary in summaries],
    }


def build_domain_bias_report(outputs: list[PredictionOutput]) -> dict[str, Any]:
    grouped: dict[str, list[PredictionOutput]] = defaultdict(list)
    for output in outputs:
        grouped[output.model_id].append(output)

    return {
        "models": [build_domain_bias_summary(model_id, model_outputs) for model_id, model_outputs in sorted(grouped.items())]
    }


def build_domain_bias_summary(model_id: str, outputs: list[PredictionOutput]) -> dict[str, Any]:
    grouped: dict[str, list[PredictionOutput]] = defaultdict(list)
    for output in outputs:
        grouped[output.product_domain].append(output)

    domains: dict[str, Any] = {}
    for product_domain, domain_outputs in sorted(grouped.items()):
        predicted_counts = Counter(output.predicted_label for output in domain_outputs)
        expected_counts = Counter(output.expected_label for output in domain_outputs)
        domains[product_domain] = {
            "sample_count": len(domain_outputs),
            "predicted_label_counts": dict(predicted_counts),
            "expected_label_counts": dict(expected_counts),
            "recall_by_label": calculate_recall_by_label(domain_outputs, expected_counts),
        }

    return {
        "model_id": model_id,
        "domains": domains,
    }


def build_quality_summary(model_id: str, outputs: list[PredictionOutput]) -> ModelQualitySummary:
    scores = [output.raw_score for output in outputs]
    predicted_counts = Counter(output.predicted_label for output in outputs)
    expected_counts = Counter(output.expected_label for output in outputs)
    recall_by_label = calculate_recall_by_label(outputs, expected_counts)
    dominant_prediction_share = max(predicted_counts.values()) / len(outputs)
    collapse_flags = build_collapse_flags(scores, dominant_prediction_share, recall_by_label)
    return ModelQualitySummary(
        model_id=model_id,
        sample_count=len(outputs),
        raw_score_min=min(scores),
        raw_score_max=max(scores),
        raw_score_unique_count=len(set(scores)),
        predicted_label_counts=dict(predicted_counts),
        expected_label_counts=dict(expected_counts),
        recall_by_label=recall_by_label,
        dominant_prediction_share=round(dominant_prediction_share, 6),
        collapse_flags=collapse_flags,
        passed_quality_gate=not collapse_flags,
    )


def calculate_recall_by_label(outputs: list[PredictionOutput], expected_counts: Counter[str]) -> dict[str, float]:
    correct_counts: Counter[str] = Counter()
    for output in outputs:
        if output.expected_label == output.predicted_label:
            correct_counts[output.expected_label] += 1
    return {
        label: round(correct_counts[label] / total, 6) if total else 0.0
        for label, total in sorted(expected_counts.items())
    }


def build_collapse_flags(scores: list[float], dominant_prediction_share: float, recall_by_label: dict[str, float]) -> list[str]:
    flags: list[str] = []
    if len(set(scores)) <= 1:
        flags.append("constant_raw_score")
    if dominant_prediction_share >= 0.95:
        flags.append("single_class_prediction_dominance")
    for label, recall in recall_by_label.items():
        if recall == 0:
            flags.append(f"zero_recall_{label}")
    return flags


def main() -> None:
    args = parse_args()
    samples = load_samples(Path(args.metadata), args.split, args.limit)
    if not samples:
        raise ValueError("No image samples were found for the requested metadata filters")

    models = select_models(args.model_id, Path(args.model_root), Path(args.active_config))
    outputs = evaluate_models(models, samples)
    payload = build_payload(outputs)
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(f"{text}\n", encoding="utf-8")
    if args.quality_report:
        quality_report = build_quality_report(outputs)
        Path(args.quality_report).write_text(f"{json.dumps(quality_report, indent=2)}\n", encoding="utf-8")
    if args.domain_bias_report:
        domain_bias_report = build_domain_bias_report(outputs)
        Path(args.domain_bias_report).write_text(f"{json.dumps(domain_bias_report, indent=2)}\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
