from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


MANIFEST_NAME = "artifact_manifest.json"


@dataclass
class ArtifactManifest:
    experiment_id: str
    model_family: str
    created_at: str
    status: str = "initialized"
    files: dict[str, str] = field(default_factory=dict)
    training: dict[str, object] = field(default_factory=dict)
    evaluation: dict[str, object] = field(default_factory=dict)
    threshold_review: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "model_family": self.model_family,
            "created_at": self.created_at,
            "status": self.status,
            "files": self.files,
            "training": self.training,
            "evaluation": self.evaluation,
            "threshold_review": self.threshold_review,
        }


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def manifest_path(model_dir: Path) -> Path:
    return model_dir / MANIFEST_NAME


def ensure_manifest(model_dir: Path, experiment_id: str, model_family: str) -> ArtifactManifest:
    path = manifest_path(model_dir)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ArtifactManifest(
            experiment_id=payload["experiment_id"],
            model_family=payload["model_family"],
            created_at=payload["created_at"],
            status=payload.get("status", "initialized"),
            files=payload.get("files", {}),
            training=payload.get("training", {}),
            evaluation=payload.get("evaluation", {}),
            threshold_review=payload.get("threshold_review", {}),
        )

    manifest = ArtifactManifest(
        experiment_id=experiment_id,
        model_family=model_family,
        created_at=utc_now_iso(),
    )
    save_manifest(model_dir, manifest)
    return manifest


def save_manifest(model_dir: Path, manifest: ArtifactManifest) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest_path(model_dir).write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")


def relative_to_model_dir(model_dir: Path, target_path: Path) -> str:
    return str(target_path.relative_to(model_dir)).replace("\\", "/")
