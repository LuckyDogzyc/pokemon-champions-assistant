from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


ENV_PREFIX = "PCA_"


@dataclass(frozen=True)
class Settings:
    api_name: str = "Pokemon Champions Assistant API"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:3000"
    frame_interval_seconds: int = 2
    video_source: str = "0"
    recognition_mode: str = "ocr"
    language: str = "zh"
    stage_recognition_enabled: bool = True
    stage_recognition_threshold: float = 0.8
    ocr_provider: str = "paddleocr"


def _get_env(name: str) -> str | None:
    return os.getenv(f"{ENV_PREFIX}{name}")


def _get_bool(name: str, default: bool) -> bool:
    value = _get_env(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = _get_env(name)
    if value is None:
        return default

    return int(value)


def _get_float(name: str, default: float) -> float:
    value = _get_env(name)
    if value is None:
        return default

    return float(value)


def _get_str(name: str, default: str) -> str:
    value = _get_env(name)
    if value is None:
        return default

    return value


@lru_cache
def get_settings() -> Settings:
    return Settings(
        api_name=_get_str("API_NAME", Settings.api_name),
        backend_port=_get_int("BACKEND_PORT", Settings.backend_port),
        frontend_origin=_get_str("FRONTEND_ORIGIN", Settings.frontend_origin),
        frame_interval_seconds=_get_int(
            "FRAME_INTERVAL_SECONDS",
            Settings.frame_interval_seconds,
        ),
        video_source=_get_str("VIDEO_SOURCE", Settings.video_source),
        recognition_mode=_get_str("RECOGNITION_MODE", Settings.recognition_mode),
        language=_get_str("LANGUAGE", Settings.language),
        stage_recognition_enabled=_get_bool(
            "STAGE_RECOGNITION_ENABLED",
            Settings.stage_recognition_enabled,
        ),
        stage_recognition_threshold=_get_float(
            "STAGE_RECOGNITION_THRESHOLD",
            Settings.stage_recognition_threshold,
        ),
        ocr_provider=_get_str("OCR_PROVIDER", Settings.ocr_provider),
    )
