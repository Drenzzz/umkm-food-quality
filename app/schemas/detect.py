from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class DetectRequest(BaseModel):
    image_url: HttpUrl


class DetectResponse(BaseModel):
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
