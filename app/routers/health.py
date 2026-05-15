from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.predictor import get_predictor
from app.schemas.admin import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("select 1"))
    predictor = get_predictor()
    return HealthResponse(
        status="ok",
        database="connected",
        model_loaded=True,
        model_version=predictor.model_version,
    )
