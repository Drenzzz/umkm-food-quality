from __future__ import annotations

import asyncio
import io
import ipaddress
import json
import socket
from functools import lru_cache
from urllib.parse import urlparse

import httpx
import numpy as np
import tflite_runtime.interpreter as tflite
from PIL import Image

from app.core.config import get_settings
from app.ml.model_registry import load_model_registry


LABEL_DISPLAY = {
    "layak_jual": {
        "label": "Layak Jual",
    },
    "tidak_layak_jual": {
        "label": "Tidak Layak Jual",
    },
}

_TIDAK_LAYAK_EXPLANATIONS = [
    (0.8, "Produk terdeteksi memiliki kerusakan visual yang signifikan — kemungkinan gosong berlebihan, hancur, atau warna yang sangat tidak normal. Tidak disarankan untuk dipasarkan."),
    (0.5, "Produk terdeteksi memiliki indikasi cacat visual yang cukup jelas — seperti warna tidak wajar, bentuk rusak, atau permukaan bercak. Sebaiknya diperiksa ulang sebelum dijual."),
    (0.0, "Produk terdeteksi memiliki indikasi cacat visual yang samar — mungkin ada perbedaan warna atau bentuk minor. Disarankan pemeriksaan manual untuk memastikan."),
]

_LAYAK_EXPLANATIONS = [
    (0.2, "Produk menunjukkan ciri visual yang sangat baik — warna, bentuk, dan kondisi permukaan tampak wajar dan layak pasarkan."),
    (0.0, "Produk menunjukkan ciri visual yang cukup baik — secara umum layak jual, namun ada sedikit variasi warna atau bentuk yang masih dalam batas wajar."),
]


def _resolve_explanation(label_key: str, raw_score: float) -> str:
    score = raw_score if label_key == "tidak_layak_jual" else 1 - raw_score
    tiers = _TIDAK_LAYAK_EXPLANATIONS if label_key == "tidak_layak_jual" else _LAYAK_EXPLANATIONS
    for threshold, explanation in tiers:
        if score >= threshold:
            return explanation
    return tiers[-1][1]


class Predictor:
    def __init__(self, interpreter: tflite.Interpreter, class_indices: dict[str, int], threshold_used: float, model_version: str) -> None:
        self.interpreter = interpreter
        self.class_indices = class_indices
        self.threshold_used = threshold_used
        self.model_version = model_version
        self.index_to_label = {index: key for key, index in class_indices.items()}
        self._input_details = interpreter.get_input_details()
        self._output_details = interpreter.get_output_details()

    async def predict_from_url(self, image_url: str) -> dict[str, float | str]:
        image_bytes = await download_image(image_url)
        # TF inference is CPU-bound and blocking; offload it to a worker thread
        # so a slow prediction does not stall the Uvicorn event loop.
        return await asyncio.to_thread(self.predict_from_image_bytes, image_bytes)

    def predict_from_image_bytes(self, image_bytes: bytes) -> dict[str, float | str]:
        tensor = preprocess_image(image_bytes)
        self.interpreter.set_tensor(self._input_details[0]["index"], tensor)
        self.interpreter.invoke()
        raw_score = float(self.interpreter.get_tensor(self._output_details[0]["index"]).flatten()[0])
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
            "explanation": _resolve_explanation(label_key, raw_score),
        }


def _validate_image_url_or_raise(image_url: str) -> None:
    settings = get_settings()
    parsed = urlparse(image_url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Image URL must use http or https scheme")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Image URL is missing a hostname")

    allowed_domains = settings.allowed_image_domain_list
    if allowed_domains:
        host_lower = hostname.lower()
        if not any(host_lower == domain or host_lower.endswith(f".{domain}") for domain in allowed_domains):
            raise ValueError("Image URL host is not in the allowed domain list")

    # Resolve hostname to an IP address and reject private, loopback, link-local,
    # multicast, and reserved ranges. This blocks SSRF attempts targeting cloud
    # metadata endpoints (e.g. 169.254.169.254) and internal infrastructure.
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Image URL host could not be resolved") from exc

    for entry in resolved:
        address = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified:
            raise ValueError("Image URL host resolves to a non-public IP address")


async def download_image(image_url: str) -> bytes:
    settings = get_settings()
    _validate_image_url_or_raise(image_url)

    max_bytes = settings.image_download_max_bytes
    timeout = settings.image_download_timeout_seconds
    max_redirects = settings.image_download_max_redirects

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=max_redirects) as client:
        try:
            async with client.stream("GET", image_url) as response:
                response.raise_for_status()

                # Re-validate the final URL to guard against open redirect chains
                # that could land on a private network host.
                if str(response.url) != image_url:
                    _validate_image_url_or_raise(str(response.url))

                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    raise ValueError("The provided URL does not point to an image resource")

                content_length_header = response.headers.get("content-length")
                if content_length_header and content_length_header.isdigit():
                    if int(content_length_header) > max_bytes:
                        raise ValueError("Image exceeds maximum allowed size")

                buffer = bytearray()
                async for chunk in response.aiter_bytes():
                    buffer.extend(chunk)
                    if len(buffer) > max_bytes:
                        raise ValueError("Image exceeds maximum allowed size")
                return bytes(buffer)
        except httpx.TooManyRedirects as exc:
            raise ValueError("Image URL exceeded the redirect limit") from exc


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        image = image.resize((224, 224), resample=Image.Resampling.LANCZOS)
        array = np.asarray(image, dtype=np.float32)
    array = np.expand_dims(array, axis=0)
    # MobileNetV2 preprocess_input: maps [0,255] to [-1,1]
    return array / 127.5 - 1.0


@lru_cache
def get_predictor() -> Predictor:
    active_model = load_model_registry().active_model
    # Resolve .tflite path: prefer .tflite if it exists alongside .keras
    model_path = active_model.model_path
    if model_path.suffix == ".keras":
        tflite_path = model_path.with_suffix(".tflite")
        if tflite_path.exists():
            model_path = tflite_path
    interpreter = tflite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    class_indices = json.loads(active_model.class_indices_path.read_text(encoding="utf-8"))
    return Predictor(
        interpreter=interpreter,
        class_indices=class_indices,
        threshold_used=active_model.threshold,
        model_version=active_model.experiment_id,
    )


@lru_cache
def get_predictor_map() -> dict[str, Predictor]:
    registry = load_model_registry()
    predictors: dict[str, Predictor] = {}
    for model_artifact in registry.models:
        model_path = model_artifact.model_path
        if model_path.suffix == ".keras":
            tflite_path = model_path.with_suffix(".tflite")
            if tflite_path.exists():
                model_path = tflite_path
        interpreter = tflite.Interpreter(model_path=str(model_path))
        interpreter.allocate_tensors()
        class_indices = json.loads(model_artifact.class_indices_path.read_text(encoding="utf-8"))
        predictors[model_artifact.experiment_id] = Predictor(
            interpreter=interpreter,
            class_indices=class_indices,
            threshold_used=model_artifact.threshold,
            model_version=model_artifact.experiment_id,
        )
    return predictors
