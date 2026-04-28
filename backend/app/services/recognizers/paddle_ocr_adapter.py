from __future__ import annotations

import base64
import binascii
import importlib
import logging
import threading
import time
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

# Minimum seconds between engine rebuilds triggered by runtime errors.
# Prevents the old bug where every OCR call rebuilt the engine (once per
# second polling loop) because the rebuilt engine failed the same way.
_REBUILD_COOLDOWN_SECONDS = 30


class PaddleOcrAdapter(OcrAdapter):
    def __init__(self, ocr_engine: Any | None = None) -> None:
        self._ocr_lock = threading.Lock()
        self._ocr_factory = None
        self._last_rebuild_time: float = 0.0
        if ocr_engine is not None:
            self._ocr_engine = ocr_engine
            return
        paddle_ocr_class = _load_paddle_ocr_class()

        def create_engine():
            # Windows portable builds crash with oneDNN fused_conv2d errors when
            # enable_mkldnn is left at its platform default (True on Windows).
            # Disabling MKL-DNN eliminates the crash with negligible performance
            # impact for the small ROI crops this app processes.  Keep cpu_threads=1
            # because the app already serializes recognition at a higher layer.
            # show_log=False suppresses the huge Namespace dump that PaddleOCR
            # prints on every __init__ call (was flooding the Windows console).
            return paddle_ocr_class(
                use_angle_cls=False, lang="ch", cpu_threads=1,
                enable_mkldnn=False, show_log=False,
            )

        self._ocr_factory = create_engine
        self._ocr_engine = create_engine()

    def read_text(self, frame: dict[str, Any], roi: dict[str, int]) -> list[dict[str, Any]]:
        roi_frame = _resolve_roi_frame(frame, roi)
        if roi_frame is None:
            return []
        image = _decode_preview_image(roi_frame.get("preview_image_data_url"))
        if image is None:
            return []
        with self._ocr_lock:
            raw_result = self._run_ocr_with_recovery(image)
        return _normalize_paddle_result(raw_result)

    def _run_ocr(self, image: Any) -> Any:
        try:
            return self._ocr_engine.ocr(image, cls=False)
        except TypeError:
            return self._ocr_engine.ocr(image)

    def _run_ocr_with_recovery(self, image: Any) -> Any:
        try:
            return self._run_ocr(image)
        except RuntimeError as exc:
            if self._ocr_factory is None or not _looks_like_recoverable_paddle_runtime_error(exc):
                raise
            logger.warning("PaddleOCR runtime error (will try rebuild): %s", exc)
            now = time.monotonic()
            if now - self._last_rebuild_time < _REBUILD_COOLDOWN_SECONDS:
                logger.warning(
                    "Skipping engine rebuild — cooldown (%.0fs remaining)",
                    _REBUILD_COOLDOWN_SECONDS - (now - self._last_rebuild_time),
                )
                return []
            self._last_rebuild_time = now
            self._ocr_engine = self._ocr_factory()
            try:
                return self._run_ocr(image)
            except RuntimeError as retry_exc:
                if _looks_like_recoverable_paddle_runtime_error(retry_exc):
                    logger.warning(
                        "PaddleOCR still fails after rebuild: %s — returning empty",
                        retry_exc,
                    )
                    return []
                raise


def _load_paddle_ocr_class():
    try:
        paddleocr_module = importlib.import_module("paddleocr")
    except ImportError:
        raise
    except Exception as exc:  # pragma: no cover - exercised via monkeypatch regression test
        raise ImportError(f"paddleocr import failed: {exc}") from exc

    paddle_ocr_class = getattr(paddleocr_module, "PaddleOCR", None)
    if paddle_ocr_class is None:
        raise ImportError("paddleocr import failed: PaddleOCR symbol is missing")
    return paddle_ocr_class


def _looks_like_recoverable_paddle_runtime_error(exc: RuntimeError) -> bool:
    message = str(exc).lower()
    recoverable_markers = (
        "onednncontext",
        "fused_conv2d",
        "predictor.run",
        "input filter",
    )
    return any(marker in message for marker in recoverable_markers)


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
