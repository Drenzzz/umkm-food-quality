from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


@dataclass(frozen=True)
class ModelArtifact:
    experiment_id: str
    model_family: str
    model_path: Path
    class_indices_path: Path
    threshold: float
    status: str
    is_active: bool


@dataclass(frozen=True)
class ModelRegistry:
    active_model: ModelArtifact
    models: list[ModelArtifact]


def load_model_registry() -> ModelRegistry:
    settings = get_settings()
    registry_root = Path(settings.model_registry_path)
    active_config = load_active_model_config(Path(settings.active_model_config_path))
    active_experiment_id = str(active_config.get("experiment_id", ""))
    models = discover_model_artifacts(registry_root, active_experiment_id)

    active_model = next((model for model in models if model.is_active), None)
    if active_model is None:
        active_model = build_env_model_artifact(settings.model_path, settings.class_indices_path)
        models = [active_model, *models]

    return ModelRegistry(active_model=active_model, models=models)


def load_active_model_config(active_config_path: Path) -> dict[str, object]:
    if not active_config_path.exists():
        return {}
    return json.loads(active_config_path.read_text(encoding="utf-8"))


def discover_model_artifacts(registry_root: Path, active_experiment_id: str) -> list[ModelArtifact]:
    if not registry_root.exists():
        return []

    artifacts: list[ModelArtifact] = []
    for model_dir in sorted(registry_root.glob("exp_*")):
        if not model_dir.is_dir():
            continue

        manifest_path = model_dir / "artifact_manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        experiment_id = str(manifest.get("experiment_id", model_dir.name))
        artifacts.append(
            ModelArtifact(
                experiment_id=experiment_id,
                model_family=str(manifest.get("model_family", "unknown")),
                model_path=model_dir / "model.keras",
                class_indices_path=model_dir / "class_indices.json",
                threshold=load_threshold(model_dir, manifest),
                status=str(manifest.get("status", "unknown")),
                is_active=experiment_id == active_experiment_id,
            )
        )

    return artifacts


def build_env_model_artifact(model_path: str, class_indices_path: str) -> ModelArtifact:
    path = Path(model_path)
    model_dir = path.parent
    manifest_path = model_dir / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    experiment_id = str(manifest.get("experiment_id", model_dir.name))
    return ModelArtifact(
        experiment_id=experiment_id,
        model_family=str(manifest.get("model_family", "unknown")),
        model_path=path,
        class_indices_path=Path(class_indices_path),
        threshold=load_threshold(model_dir, manifest),
        status=str(manifest.get("status", "unknown")),
        is_active=True,
    )


def load_threshold(model_dir: Path, manifest: dict[str, object]) -> float:
    review = manifest.get("threshold_review")
    if isinstance(review, dict) and "recommended_threshold" in review:
        return float(review["recommended_threshold"])

    threshold_path = model_dir / "evaluation" / "threshold_review.json"
    if threshold_path.exists():
        payload = json.loads(threshold_path.read_text(encoding="utf-8"))
        recommended = payload.get("recommended_threshold")
        if isinstance(recommended, dict) and "threshold" in recommended:
            return float(recommended["threshold"])
        if isinstance(recommended, int | float):
            return float(recommended)

    evaluation = manifest.get("evaluation")
    if isinstance(evaluation, dict) and "threshold" in evaluation:
        return float(evaluation["threshold"])

    return 0.5
