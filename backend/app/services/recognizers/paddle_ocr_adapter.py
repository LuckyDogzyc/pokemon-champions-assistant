from __future__ import annotations

import base64
import binascii
import importlib
import logging
from pathlib import Path
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

# ── ONNX model helpers ───────────────────────────────────────────────────
# PaddleOCR on Windows portable builds crashes with oneDNN fused_conv2d
# RuntimeError regardless of enable_mkldnn=False or FLAGS_use_mkldnn=0.
# The only reliable fix is to use ONNX Runtime inference (use_onnx=True)
# which completely bypasses paddle inference and oneDNN.
# This adapter is ONNX-only — no paddlepaddle inference dependency.


def _paddle_model_base_dir() -> Path:
    """Return the PaddleOCR model root directory (``~/.paddleocr/whl``)."""
    return Path.home() / ".paddleocr" / "whl"


def _paddle_model_dirs() -> list[tuple[str, Path]]:
    """Return (role, model_dir) pairs for det / cls / rec models."""
    base = _paddle_model_base_dir()
    candidates: list[tuple[str, Path]] = []
    # PP-OCRv4 det
    det = base / "det" / "ch" / "ch_PP-OCRv4_det_infer"
    if det.is_dir():
        candidates.append(("det", det))
    # cls v2
    cls = base / "cls" / "ch_ppocr_mobile_v2.0_cls_infer"
    if cls.is_dir():
        candidates.append(("cls", cls))
    # PP-OCRv4 rec
    rec = base / "rec" / "ch" / "ch_PP-OCRv4_rec_infer"
    if rec.is_dir():
        candidates.append(("rec", rec))
    return candidates


def _ensure_onnx_models() -> dict[str, str]:
    """Convert Paddle models to ONNX if needed and return the model-dir
    kwargs for PaddleOCR(use_onnx=True).

    Raises ImportError if paddle2onnx is not installed.
    Raises FileNotFoundError if no Paddle model dirs are found.
    """
    try:
        import paddle2onnx  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "paddle2onnx is required for ONNX-based OCR but not installed"
        ) from exc

    dirs = _paddle_model_dirs()
    if not dirs:
        raise FileNotFoundError(
            "No PaddleOCR Paddle model dirs found for ONNX conversion — "
            "run the app once with paddlepaddle installed to download models, "
            "or copy model files to ~/.paddleocr/whl/"
        )

    onnx_paths: dict[str, str] = {}
    for role, model_dir in dirs:
        onnx_file = model_dir / "inference.onnx"
        pdmodel = model_dir / "inference.pdmodel"
        pdiparams = model_dir / "inference.pdiparams"

        if onnx_file.exists():
            onnx_paths[f"{role}_model_dir"] = str(onnx_file)
            continue

        # Need to convert — both .pdmodel and .pdiparams must exist
        if not pdmodel.exists() or not pdiparams.exists():
            raise FileNotFoundError(
                f"Cannot convert {role}: missing .pdmodel or .pdiparams in {model_dir}"
            )

        logger.info("Converting %s model to ONNX: %s", role, model_dir)
        paddle2onnx.export(
            str(pdmodel),
            str(pdiparams),
            save_file=str(onnx_file),
            opset_version=14,
            enable_onnx_checker=True,
        )
        onnx_paths[f"{role}_model_dir"] = str(onnx_file)
        logger.info("  -> %s (%.1f MB)", onnx_file.name, onnx_file.stat().st_size / 1024 / 1024)

    if not onnx_paths:
        raise FileNotFoundError("No ONNX models could be prepared")

    return onnx_paths


class PaddleOcrAdapter(OcrAdapter):
    """ONNX-only PaddleOCR adapter — no paddlepaddle inference dependency."""

    def __init__(self, ocr_engine: Any | None = None) -> None:
        if ocr_engine is not None:
            self._ocr_engine = ocr_engine
            return

        import onnxruntime  # noqa: F401 – verify available

        paddle_ocr_class = _load_paddle_ocr_class()
        onnx_kwargs = _ensure_onnx_models()

        self._ocr_engine = paddle_ocr_class(
            use_onnx=True,
            use_angle_cls=False,
            lang="ch",
            show_log=False,
            onnx_providers=["CPUExecutionProvider"],
            **onnx_kwargs,
        )
        logger.info("PaddleOCR initialized with ONNX Runtime backend")

    def read_text(self, frame: dict[str, Any], roi: dict[str, int]) -> list[dict[str, Any]]:
        roi_frame = _resolve_roi_frame(frame, roi)
        if roi_frame is None:
            return []
        image = _decode_preview_image(roi_frame.get("preview_image_data_url"))
        if image is None:
            return []
        raw_result = self._run_ocr(image)
        return _normalize_paddle_result(raw_result)

    def _run_ocr(self, image: Any) -> Any:
        try:
            return self._ocr_engine.ocr(image, cls=False)
        except TypeError:
            return self._ocr_engine.ocr(image)


def _load_paddle_ocr_class():
    try:
        paddleocr_module = importlib.import_module("paddleocr")
    except ImportError:
        raise
    except Exception as exc:
        raise ImportError(f"paddleocr import failed: {exc}") from exc

    paddle_ocr_class = getattr(paddleocr_module, "PaddleOCR", None)
    if paddle_ocr_class is None:
        raise ImportError("paddleocr import failed: PaddleOCR symbol is missing")
    return paddle_ocr_class


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
