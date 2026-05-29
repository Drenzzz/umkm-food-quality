from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class DetectRequest(BaseModel):
    image_url: HttpUrl


class DetectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

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


class ModelComparisonItemResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    label: str
    label_key: str
    confidence_score: float
    raw_score: float
    threshold_used: float
    explanation: str
    is_active: bool
    passed_quality_gate: bool | None
    collapse_flags: list[str]


class DetectComparisonResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    active_model_id: str
    image_url: str
    predictions: list[ModelComparisonItemResponse]
