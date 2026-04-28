from __future__ import annotations

import base64
import binascii
import logging
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from app.services.recognizers.ocr_adapter import OcrAdapter
from app.services.roi_capture import build_roi_frame

logger = logging.getLogger(__name__)

# ── RapidOCR (pure ONNX, no paddlepaddle) ─────────────────────────────────
# PaddleOCR on Windows portable builds crashes with oneDNN fused_conv2d
# RuntimeError regardless of enable_mkldnn=False or FLAGS_use_mkldnn=0.
# Additionally, the paddleocr Python package has a hard dependency on
# paddlepaddle at import time (from paddle.utils import try_import),
# so removing paddlepaddle from deps breaks `import paddleocr` entirely.
#
# RapidOCR is a paddle-free fork that uses ONNX Runtime directly —
# no paddlepaddle, no paddle2onnx, no model conversion needed.


class PaddleOcrAdapter(OcrAdapter):
    """ONNX-only OCR adapter using RapidOCR — no paddlepaddle dependency."""

    def __init__(self, ocr_engine: Any | None = None) -> None:
        if ocr_engine is not None:
            self._ocr_engine = ocr_engine
            return

        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "rapidocr-onnxruntime is required for OCR but not installed. "
                "Install with: pip install rapidocr-onnxruntime"
            ) from exc

        self._ocr_engine = RapidOCR()
        logger.info("RapidOCR (ONNX Runtime) initialized")

    def read_text(self, frame: dict[str, Any], roi: dict[str, int]) -> list[dict[str, Any]]:
        roi_frame = _resolve_roi_frame(frame, roi)
        if roi_frame is None:
            return []
        image = _decode_preview_image(roi_frame.get("preview_image_data_url"))
        if image is None:
            return []
        raw_result = self._run_ocr(image)
        return _normalize_rapid_result(raw_result)

    def _run_ocr(self, image: Any) -> Any:
        result, _ = self._ocr_engine(image)
        return result


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


def _normalize_rapid_result(raw_result: Any) -> list[dict[str, Any]]:
    """Normalize RapidOCR output to the standard [{text, score}] format.

    RapidOCR returns a list of [bbox, text, confidence] or None.
    """
    if raw_result is None:
        return []

    normalized: list[dict[str, Any]] = []
    for entry in raw_result:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        text = str(entry[1]).strip()
        if not text:
            continue
        try:
            score = float(entry[2])
        except (TypeError, ValueError):
            score = 0.0
        normalized.append({"text": text, "score": score})
    return normalized
