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


class AdminDetectionListResponse(BaseModel):
    items: list[AdminDetectionItemResponse]


class HealthResponse(BaseModel):
    status: str
    database: str
    model_loaded: bool
    model_version: str
