from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import HistoryDetailResponse, HistoryItemResponse, HistoryListResponse
from app.services.history_service import get_latest_detection, get_user_detection, list_user_history


router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
def read_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> HistoryListResponse:
    items = [HistoryItemResponse.model_validate(item) for item in list_user_history(db, current_user)]
    return HistoryListResponse(items=items)


@router.get("/history/latest", response_model=HistoryDetailResponse)
def read_latest_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryDetailResponse:
    detection = get_latest_detection(db, current_user)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No detection history found")
    return HistoryDetailResponse.model_validate(detection)


@router.get("/history/{detection_id}", response_model=HistoryDetailResponse)
def read_history_detail(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryDetailResponse:
    detection = get_user_detection(db, current_user, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    return HistoryDetailResponse.model_validate(detection)
