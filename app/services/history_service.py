from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Detection, User


def list_user_history(db: Session, user: User) -> list[Detection]:
    statement = select(Detection).where(Detection.user_id == user.id).order_by(Detection.created_at.desc())
    return list(db.scalars(statement))


def get_user_detection(db: Session, user: User, detection_id: int) -> Detection | None:
    statement = select(Detection).where(Detection.id == detection_id, Detection.user_id == user.id)
    return db.scalar(statement)
