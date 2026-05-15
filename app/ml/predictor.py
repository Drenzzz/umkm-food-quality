from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path

import httpx
import numpy as np
import tensorflow as tf
from PIL import Image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

from app.core.config import get_settings


LABEL_DISPLAY = {
    "layak_jual": {
        "label": "Layak Jual",
        "explanation": "Produk memenuhi indikator visual kelayakan seperti warna normal, bentuk relatif utuh, dan kondisi permukaan yang wajar.",
    },
    "tidak_layak_jual": {
        "label": "Tidak Layak Jual",
        "explanation": "Produk terdeteksi memiliki indikasi cacat visual seperti warna tidak normal, kerusakan bentuk, atau kondisi permukaan yang tidak wajar.",
    },
}


class Predictor:
    def __init__(self, model: tf.keras.Model, class_indices: dict[str, int], threshold_used: float, model_version: str) -> None:
        self.model = model
        self.class_indices = class_indices
        self.threshold_used = threshold_used
        self.model_version = model_version
        self.index_to_label = {index: key for key, index in class_indices.items()}

    async def predict_from_url(self, image_url: str) -> dict[str, float | str]:
        image_bytes = await download_image(image_url)
        tensor = preprocess_image(image_bytes)
        raw_score = float(self.model.predict(tensor, verbose=0).flatten()[0])
        return self._map_prediction(raw_score)

    def _map_prediction(self, raw_score: float) -> dict[str, float | str]:
        target_index = 1 if raw_score >= self.threshold_used else 0
        label_key = self.index_to_label[target_index]
        confidence = raw_score if target_index == 1 else 1 - raw_score
        display = LABEL_DISPLAY[label_key]
        return {
            "label": display["label"],
            "label_key": label_key,
            "confidence_score": round(confidence * 100, 2),
            "raw_score": round(raw_score, 6),
            "threshold_used": self.threshold_used,
            "model_version": self.model_version,
            "explanation": display["explanation"],
        }


async def download_image(image_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError("The provided URL does not point to an image resource")
        return response.content


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        image = image.resize((224, 224), resample=Image.Resampling.LANCZOS)
        array = np.asarray(image, dtype=np.float32)
    array = np.expand_dims(array, axis=0)
    return preprocess_input(array)


def load_threshold(model_dir: Path) -> float:
    threshold_path = model_dir / "evaluation" / "threshold_review.json"
    if threshold_path.exists():
        payload = json.loads(threshold_path.read_text(encoding="utf-8"))
        return float(payload["recommended_threshold"]["threshold"])
    return 0.5


def load_model_version(model_dir: Path) -> str:
    manifest_path = model_dir / "artifact_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return payload.get("experiment_id", model_dir.name)
    return model_dir.name


@lru_cache
def get_predictor() -> Predictor:
    settings = get_settings()
    model_path = Path(settings.model_path)
    class_indices_path = Path(settings.class_indices_path)
    model_dir = model_path.parent

    model = tf.keras.models.load_model(model_path)
    class_indices = json.loads(class_indices_path.read_text(encoding="utf-8"))
    threshold_used = load_threshold(model_dir)
    model_version = load_model_version(model_dir)
    return Predictor(model=model, class_indices=class_indices, threshold_used=threshold_used, model_version=model_version)
