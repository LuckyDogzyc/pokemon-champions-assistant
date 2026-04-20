from __future__ import annotations

import base64
import binascii
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover
    PaddleOCR = None

from app.services.recognizers.ocr_adapter import OcrAdapter
from app.services.roi_capture import build_roi_frame


class PaddleOcrAdapter(OcrAdapter):
    def __init__(self, ocr_engine: Any | None = None) -> None:
        if ocr_engine is not None:
            self._ocr_engine = ocr_engine
            return
        if PaddleOCR is None:
            raise ImportError("paddleocr is not installed")
        self._ocr_engine = PaddleOCR(use_angle_cls=False, lang="ch")

    def read_text(self, frame: dict[str, Any], roi: dict[str, int]) -> list[dict[str, Any]]:
        roi_frame = _resolve_roi_frame(frame, roi)
        if roi_frame is None:
            return []
        image = _decode_preview_image(roi_frame.get("preview_image_data_url"))
        if image is None:
            return []
        try:
            raw_result = self._ocr_engine.ocr(image, cls=False)
        except TypeError:
            raw_result = self._ocr_engine.ocr(image)
        return _normalize_paddle_result(raw_result)


def _resolve_roi_frame(frame: dict[str, Any], roi: dict[str, int]) -> dict[str, Any] | None:
    if frame.get("preview_image_data_url") and frame.get("source_preview_image_data_url"):
        return frame
    return build_roi_frame(frame, roi)


def _decode_preview_image(preview_image_data_url: str | None):
    if not preview_image_data_url or cv2 is None or np is None:
        return None
    if not preview_image_data_url.startswith("data:") or "," not in preview_image_data_url:
        return None

    _, encoded = preview_image_data_url.split(",", 1)
    try:
        image_bytes = base64.b64decode(encoded)
    except (binascii.Error, ValueError):
        return None

    try:
        return cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), getattr(cv2, "IMREAD_COLOR", 1))
    except Exception:
        return None


def _normalize_paddle_result(raw_result: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in _iter_ocr_entries(raw_result):
        parsed = _parse_ocr_entry(entry)
        if parsed is not None:
            normalized.append(parsed)
    return normalized


def _iter_ocr_entries(node: Any):
    if isinstance(node, dict):
        yield node
        return
    if isinstance(node, (list, tuple)):
        if _looks_like_paddle_line(node):
            yield node
            return
        for child in node:
            yield from _iter_ocr_entries(child)


def _looks_like_paddle_line(node: Any) -> bool:
    if not isinstance(node, (list, tuple)) or len(node) < 2:
        return False
    tail = node[-1]
    return isinstance(tail, (list, tuple)) and len(tail) >= 1 and isinstance(tail[0], str)


def _parse_ocr_entry(entry: Any) -> dict[str, Any] | None:
    if isinstance(entry, dict):
        text = str(entry.get("text") or entry.get("transcription") or "").strip()
        score = float(entry.get("score") or entry.get("confidence") or 0.0)
        return {"text": text, "score": score} if text else None

    if _looks_like_paddle_line(entry):
        text = str(entry[-1][0]).strip()
        if not text:
            return None
        score = float(entry[-1][1]) if len(entry[-1]) > 1 else 0.0
        return {"text": text, "score": score}

    return None
