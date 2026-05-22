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
    passed_quality_gate: bool | None
    collapse_flags: list[str]
    quality_sample_count: int | None


@dataclass(frozen=True)
class ModelRegistry:
    active_model: ModelArtifact
    models: list[ModelArtifact]


def load_model_registry() -> ModelRegistry:
    settings = get_settings()
    registry_root = Path(settings.model_registry_path)
    active_config = load_active_model_config(Path(settings.active_model_config_path))
    quality_report = load_model_quality_report(Path(settings.model_quality_report_path))
    active_experiment_id = str(active_config.get("experiment_id", ""))
    models = discover_model_artifacts(registry_root, active_experiment_id, quality_report)

    active_model = next((model for model in models if model.is_active), None)
    if active_model is None:
        active_model = build_env_model_artifact(settings.model_path, settings.class_indices_path, quality_report)
        models = [active_model, *models]

    enforce_active_model_quality(active_model, settings.model_quality_strict)

    return ModelRegistry(active_model=active_model, models=models)


def load_active_model_config(active_config_path: Path) -> dict[str, object]:
    if not active_config_path.exists():
        return {}
    return json.loads(active_config_path.read_text(encoding="utf-8"))


def load_model_quality_report(quality_report_path: Path) -> dict[str, dict[str, object]]:
    if not quality_report_path.exists():
        return {}

    payload = json.loads(quality_report_path.read_text(encoding="utf-8"))
    items = payload.get("models", [])
    if not isinstance(items, list):
        return {}

    report: dict[str, dict[str, object]] = {}
    for item in items:
        if isinstance(item, dict) and "model_id" in item:
            report[str(item["model_id"])] = item
    return report


def discover_model_artifacts(registry_root: Path, active_experiment_id: str, quality_report: dict[str, dict[str, object]]) -> list[ModelArtifact]:
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
                passed_quality_gate=load_quality_passed(quality_report, experiment_id),
                collapse_flags=load_quality_flags(quality_report, experiment_id),
                quality_sample_count=load_quality_sample_count(quality_report, experiment_id),
            )
        )

    return artifacts


def build_env_model_artifact(model_path: str, class_indices_path: str, quality_report: dict[str, dict[str, object]]) -> ModelArtifact:
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
        passed_quality_gate=load_quality_passed(quality_report, experiment_id),
        collapse_flags=load_quality_flags(quality_report, experiment_id),
        quality_sample_count=load_quality_sample_count(quality_report, experiment_id),
    )


def load_quality_passed(quality_report: dict[str, dict[str, object]], experiment_id: str) -> bool | None:
    item = quality_report.get(experiment_id)
    if item is None or "passed_quality_gate" not in item:
        return None
    return bool(item["passed_quality_gate"])


def load_quality_flags(quality_report: dict[str, dict[str, object]], experiment_id: str) -> list[str]:
    item = quality_report.get(experiment_id)
    if item is None:
        return []

    flags = item.get("collapse_flags", [])
    if not isinstance(flags, list):
        return []
    return [str(flag) for flag in flags]


def load_quality_sample_count(quality_report: dict[str, dict[str, object]], experiment_id: str) -> int | None:
    item = quality_report.get(experiment_id)
    if item is None or "sample_count" not in item:
        return None
    return int(item["sample_count"])


def enforce_active_model_quality(active_model: ModelArtifact, strict_mode: bool) -> None:
    if not strict_mode or active_model.passed_quality_gate is not False:
        return

    flags = ", ".join(active_model.collapse_flags) or "quality_gate_failed"
    raise RuntimeError(f"Active model '{active_model.experiment_id}' failed quality gate: {flags}")


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
