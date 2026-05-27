from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.core.limiter import limiter
from app.ml.predictor import get_predictor
from app.schemas.detect import DetectRequest, DetectResponse
from app.services.detect_service import create_detection


router = APIRouter(prefix="", tags=["detect"])


@router.post("/detect", response_model=DetectResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def detect_product(
    request: Request,
    payload: DetectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DetectResponse:
    try:
        detection = await create_detection(db, get_predictor(), current_user, str(payload.image_url))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        settings = get_settings()
        if settings.app_env in {"development", "test"}:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Detection failed: {exc}") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Detection failed") from None

    return DetectResponse.model_validate(detection)
