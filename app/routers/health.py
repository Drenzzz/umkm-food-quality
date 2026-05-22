from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.model_registry import load_model_registry
from app.schemas.admin import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("select 1"))
    active_model = load_model_registry().active_model
    return HealthResponse(
        status="ok",
        database="connected",
        model_loaded=active_model.model_path.exists(),
        model_version=active_model.experiment_id,
    )
