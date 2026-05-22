from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Detection
from app.ml.predictor import get_predictor


def get_dashboard_summary(db: Session) -> dict[str, int | str]:
    total_detections = db.scalar(select(func.count()).select_from(Detection)) or 0
    total_layak_jual = db.scalar(select(func.count()).select_from(Detection).where(Detection.label_key == "layak_jual")) or 0
    total_tidak_layak_jual = db.scalar(select(func.count()).select_from(Detection).where(Detection.label_key == "tidak_layak_jual")) or 0
    predictor = get_predictor()
    return {
        "total_detections": int(total_detections),
        "total_layak_jual": int(total_layak_jual),
        "total_tidak_layak_jual": int(total_tidak_layak_jual),
        "active_model_version": predictor.model_version,
    }


def list_all_detections(db: Session) -> list[Detection]:
    statement = select(Detection).order_by(Detection.created_at.desc())
    return list(db.scalars(statement))


def get_detection_detail(db: Session, detection_id: int) -> Detection | None:
    statement = select(Detection).where(Detection.id == detection_id)
    return db.scalar(statement)
