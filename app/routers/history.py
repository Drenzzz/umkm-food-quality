from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import BulkDeleteRequest, DeleteHistoryResponse, HistoryDetailResponse, HistoryItemResponse, HistoryListResponse
from app.services.history_service import (
    count_user_history,
    delete_user_detection,
    delete_user_detections_bulk,
    get_latest_detection,
    get_user_detection,
    list_user_history,
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
)


router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
def read_history(
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_HISTORY_LIMIT, ge=1, le=MAX_HISTORY_LIMIT),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryListResponse:
    total = count_user_history(db, current_user)
    items = [HistoryItemResponse.model_validate(item) for item in list_user_history(db, current_user, offset, limit)]
    return HistoryListResponse(items=items, total=total, offset=offset, limit=limit)


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


@router.delete("/history/{detection_id}", response_model=DeleteHistoryResponse)
def delete_history_detail(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteHistoryResponse:
    deleted = delete_user_detection(db, current_user, detection_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    return DeleteHistoryResponse(deleted_count=1)


@router.delete("/history", response_model=DeleteHistoryResponse)
def delete_history_bulk(
    payload: BulkDeleteRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteHistoryResponse:
    deleted_count = delete_user_detections_bulk(db, current_user, payload.ids)
    return DeleteHistoryResponse(deleted_count=deleted_count)
