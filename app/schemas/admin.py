from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    label_key: str
    confidence_score: float
    image_url: str
    created_at: datetime


class HistoryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    label_key: str
    confidence_score: float
    raw_score: float
    threshold_used: float
    model_version: str
    explanation: str
    image_url: str
    created_at: datetime


class HistoryListResponse(BaseModel):
    items: list[HistoryItemResponse]


class AdminDashboardResponse(BaseModel):
    total_detections: int
    total_layak_jual: int
    total_tidak_layak_jual: int
    active_model_version: str


class AdminDetectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    label: str
    label_key: str
    confidence_score: float
    model_version: str
    created_at: datetime


class AdminDetectionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    label: str
    label_key: str
    confidence_score: float
    raw_score: float
    threshold_used: float
    model_version: str
    explanation: str
    image_url: str
    created_at: datetime
    active_model_id: str
    prediction_mode: str
    class_indices: dict[str, int]


class AdminDetectionListResponse(BaseModel):
    items: list[AdminDetectionItemResponse]


class AdminModelItemResponse(BaseModel):
    experiment_id: str
    model_family: str
    threshold: float
    status: str
    is_active: bool
    model_file_available: bool
    class_indices_file_available: bool


class AdminModelRegistryResponse(BaseModel):
    active_model_id: str
    models: list[AdminModelItemResponse]


class HealthResponse(BaseModel):
    status: str
    database: str
    model_loaded: bool
    model_version: str
