from sqlalchemy.orm import Session

from app.db.models import Detection, User
from app.ml.predictor import Predictor


async def create_detection(db: Session, predictor: Predictor, user: User, image_url: str) -> Detection:
    prediction = await predictor.predict_from_url(image_url)
    detection = Detection(
        user_id=user.id,
        image_url=image_url,
        label=str(prediction["label"]),
        label_key=str(prediction["label_key"]),
        confidence_score=float(prediction["confidence_score"]),
        raw_score=float(prediction["raw_score"]),
        threshold_used=float(prediction["threshold_used"]),
        model_version=str(prediction["model_version"]),
        explanation=str(prediction["explanation"]),
        heatmap_base64=prediction.get("heatmap_base64"),
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection
