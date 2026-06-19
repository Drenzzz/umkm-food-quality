from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_admin
from app.db.models import User
from app.db.session import get_db
from app.ml.model_registry import load_model_registry
from app.ml.predictor import download_image, get_predictor_map
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminDetectionDetailResponse,
    AdminDetectionItemResponse,
    AdminDetectionListResponse,
    AdminModelRegistryResponse,
)
from app.schemas.detect import DetectComparisonResponse, DetectRequest, ModelComparisonItemResponse
from app.services.admin_service import (
    build_detection_detail_response,
    count_all_detections,
    get_dashboard_summary,
    get_detection_detail,
    get_model_registry_metadata,
    list_all_detections,
    DEFAULT_ADMIN_LIMIT,
    MAX_ADMIN_LIMIT,
)


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def read_admin_dashboard(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminDashboardResponse:
    summary = get_dashboard_summary(db)
    return AdminDashboardResponse(**summary)


@router.get("/models", response_model=AdminModelRegistryResponse)
def read_admin_models(_: User = Depends(require_admin)) -> AdminModelRegistryResponse:
    return get_model_registry_metadata()


@router.post("/detect/compare", response_model=DetectComparisonResponse)
async def compare_admin_detection_models(
    payload: DetectRequest,
    _: User = Depends(require_admin),
) -> DetectComparisonResponse:
    settings = get_settings()
    if not settings.enable_multi_model_comparison:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Multi-model comparison is disabled")

    registry = load_model_registry()
    image_bytes = await download_image(str(payload.image_url))
    predictor_map = get_predictor_map()

    predictions: list[ModelComparisonItemResponse] = []
    for model_artifact in registry.models:
        predictor = predictor_map[model_artifact.experiment_id]
        result = predictor.predict_from_image_bytes(image_bytes)
        predictions.append(
            ModelComparisonItemResponse(
                model_version=model_artifact.experiment_id,
                label=str(result["label"]),
                label_key=str(result["label_key"]),
                confidence_score=float(result["confidence_score"]),
                raw_score=float(result["raw_score"]),
                threshold_used=float(result["threshold_used"]),
                explanation=str(result["explanation"]),
                is_active=model_artifact.is_active,
                passed_quality_gate=model_artifact.passed_quality_gate,
                collapse_flags=model_artifact.collapse_flags,
            )
        )

    return DetectComparisonResponse(
        active_model_id=registry.active_model.experiment_id,
        image_url=str(payload.image_url),
        predictions=predictions,
    )


@router.get("/detections", response_model=AdminDetectionListResponse)
def read_admin_detections(
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_ADMIN_LIMIT, ge=1, le=MAX_ADMIN_LIMIT),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDetectionListResponse:
    total = count_all_detections(db)
    items = [AdminDetectionItemResponse.model_validate(item) for item in list_all_detections(db, offset, limit)]
    return AdminDetectionListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/detections/{detection_id}", response_model=AdminDetectionDetailResponse)
def read_admin_detection_detail(
    detection_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminDetectionDetailResponse:
    detection = get_detection_detail(db, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    return build_detection_detail_response(detection)
