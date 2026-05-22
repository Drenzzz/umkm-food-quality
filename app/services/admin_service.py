import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Detection
from app.ml.model_registry import ModelArtifact, load_model_registry
from app.schemas.admin import AdminDetectionDetailResponse, AdminModelItemResponse, AdminModelRegistryResponse


def get_dashboard_summary(db: Session) -> dict[str, int | str]:
    total_detections = db.scalar(select(func.count()).select_from(Detection)) or 0
    total_layak_jual = db.scalar(select(func.count()).select_from(Detection).where(Detection.label_key == "layak_jual")) or 0
    total_tidak_layak_jual = db.scalar(select(func.count()).select_from(Detection).where(Detection.label_key == "tidak_layak_jual")) or 0
    active_model = load_model_registry().active_model
    return {
        "total_detections": int(total_detections),
        "total_layak_jual": int(total_layak_jual),
        "total_tidak_layak_jual": int(total_tidak_layak_jual),
        "active_model_version": active_model.experiment_id,
    }


def list_all_detections(db: Session) -> list[Detection]:
    statement = select(Detection).order_by(Detection.created_at.desc())
    return list(db.scalars(statement))


def get_detection_detail(db: Session, detection_id: int) -> Detection | None:
    statement = select(Detection).where(Detection.id == detection_id)
    return db.scalar(statement)


def build_detection_detail_response(detection: Detection) -> AdminDetectionDetailResponse:
    registry = load_model_registry()
    active_model = registry.active_model
    return AdminDetectionDetailResponse(
        id=detection.id,
        user_id=detection.user_id,
        label=detection.label,
        label_key=detection.label_key,
        confidence_score=detection.confidence_score,
        raw_score=detection.raw_score,
        threshold_used=detection.threshold_used,
        model_version=detection.model_version,
        explanation=detection.explanation,
        image_url=detection.image_url,
        created_at=detection.created_at,
        active_model_id=active_model.experiment_id,
        prediction_mode="single_active_model",
        class_indices=load_class_indices(active_model),
    )


def get_model_registry_metadata() -> AdminModelRegistryResponse:
    registry = load_model_registry()
    return AdminModelRegistryResponse(
        active_model_id=registry.active_model.experiment_id,
        models=[build_model_item(model) for model in registry.models],
    )


def build_model_item(model: ModelArtifact) -> AdminModelItemResponse:
    return AdminModelItemResponse(
        experiment_id=model.experiment_id,
        model_family=model.model_family,
        threshold=model.threshold,
        status=model.status,
        is_active=model.is_active,
        model_file_available=model.model_path.exists(),
        class_indices_file_available=model.class_indices_path.exists(),
    )


def load_class_indices(model: ModelArtifact) -> dict[str, int]:
    if not model.class_indices_path.exists():
        return {}
    payload = json.loads(model.class_indices_path.read_text(encoding="utf-8"))
    return {str(key): int(value) for key, value in payload.items()}
