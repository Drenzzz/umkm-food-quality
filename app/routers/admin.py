from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminDetectionDetailResponse,
    AdminDetectionItemResponse,
    AdminDetectionListResponse,
    AdminModelRegistryResponse,
)
from app.services.admin_service import get_dashboard_summary, get_detection_detail, get_model_registry_metadata, list_all_detections


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def read_admin_dashboard(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminDashboardResponse:
    summary = get_dashboard_summary(db)
    return AdminDashboardResponse(**summary)


@router.get("/models", response_model=AdminModelRegistryResponse)
def read_admin_models(_: User = Depends(require_admin)) -> AdminModelRegistryResponse:
    return get_model_registry_metadata()


@router.get("/detections", response_model=AdminDetectionListResponse)
def read_admin_detections(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminDetectionListResponse:
    items = [AdminDetectionItemResponse.model_validate(item) for item in list_all_detections(db)]
    return AdminDetectionListResponse(items=items)


@router.get("/detections/{detection_id}", response_model=AdminDetectionDetailResponse)
def read_admin_detection_detail(
    detection_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDetectionDetailResponse:
    detection = get_detection_detail(db, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    return AdminDetectionDetailResponse.model_validate(detection)
