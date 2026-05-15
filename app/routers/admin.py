from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import AdminDashboardResponse, AdminDetectionItemResponse, AdminDetectionListResponse
from app.services.admin_service import get_dashboard_summary, list_all_detections


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def read_admin_dashboard(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminDashboardResponse:
    summary = get_dashboard_summary(db)
    return AdminDashboardResponse(**summary)


@router.get("/detections", response_model=AdminDetectionListResponse)
def read_admin_detections(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminDetectionListResponse:
    items = [AdminDetectionItemResponse.model_validate(item) for item in list_all_detections(db)]
    return AdminDetectionListResponse(items=items)
