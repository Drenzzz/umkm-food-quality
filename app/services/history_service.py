from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Detection, User


def list_user_history(db: Session, user: User) -> list[Detection]:
    statement = select(Detection).where(Detection.user_id == user.id).order_by(Detection.created_at.desc())
    return list(db.scalars(statement))


def get_user_detection(db: Session, user: User, detection_id: int) -> Detection | None:
    statement = select(Detection).where(Detection.id == detection_id, Detection.user_id == user.id)
    return db.scalar(statement)


def get_latest_detection(db: Session, user: User) -> Detection | None:
    statement = select(Detection).where(Detection.user_id == user.id).order_by(Detection.created_at.desc()).limit(1)
    return db.scalar(statement)


def delete_user_detection(db: Session, user: User, detection_id: int) -> bool:
    result = db.execute(delete(Detection).where(Detection.id == detection_id, Detection.user_id == user.id))
    db.commit()
    return (result.rowcount or 0) > 0


def delete_user_detections_bulk(db: Session, user: User, detection_ids: list[int]) -> int:
    if not detection_ids:
        return 0

    result = db.execute(delete(Detection).where(Detection.user_id == user.id, Detection.id.in_(detection_ids)))
    db.commit()
    return int(result.rowcount or 0)
