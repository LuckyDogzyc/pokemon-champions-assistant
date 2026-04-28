import pytest

from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter, _normalize_rapid_result

# Skip the entire module when OCR optional deps are not installed.
pytest.importorskip("rapidocr_onnxruntime", reason="rapidocr-onnxruntime not installed")


class StubOcrEngine:
    """Mimics RapidOCR's return shape: (result, elapse) where result is list or None."""

    def __call__(self, image):
        return [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], "喷火龙", 0.97],
        ], None


def test_normalize_rapid_result_with_standard_output():
    raw = [
        [[[0, 0], [1, 0], [1, 1], [0, 1]], "皮卡丘", 0.88],
        [[[0, 0], [1, 0], [1, 1], [0, 1]], "妙蛙种子", 0.95],
    ]
    normalized = _normalize_rapid_result(raw)

    assert normalized == [
        {"text": "皮卡丘", "score": 0.88},
        {"text": "妙蛙种子", "score": 0.95},
    ]


def test_normalize_rapid_result_with_none():
    """RapidOCR returns None when no text is detected."""
    assert _normalize_rapid_result(None) == []


def test_normalize_rapid_result_skips_empty_text():
    raw = [
        [[[0, 0], [1, 0], [1, 1], [0, 1]], "", 0.5],
        [[[0, 0], [1, 0], [1, 1], [0, 1]], "  ", 0.6],
        [[[0, 0], [1, 0], [1, 1], [0, 1]], "有效文本", 0.9],
    ]
    normalized = _normalize_rapid_result(raw)
    assert len(normalized) == 1
    assert normalized[0]["text"] == "有效文本"


def test_normalize_rapid_result_handles_malformed_entry():
    raw = [
        ["not-enough-elements"],
        [[[0, 0], [1, 0], [1, 1], [0, 1]], "好", 0.9],
    ]
    normalized = _normalize_rapid_result(raw)
    assert len(normalized) == 1
    assert normalized[0]["text"] == "好"


def test_paddle_ocr_adapter_raises_when_rapidocr_missing(monkeypatch):
    """If rapidocr_onnxruntime is not importable, adapter should raise ImportError."""
    from app.services.recognizers import paddle_ocr_adapter
    import builtins
    import sys

    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "rapidocr_onnxruntime":
            raise ImportError("no module named 'rapidocr_onnxruntime'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    sys.modules.pop("rapidocr_onnxruntime", None)

    try:
        PaddleOcrAdapter()
        raise AssertionError("expected ImportError when rapidocr_onnxruntime is missing")
    except ImportError as exc:
        assert "rapidocr-onnxruntime" in str(exc).lower()


def test_paddle_ocr_adapter_returns_normalized_texts(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter(ocr_engine=StubOcrEngine())
    result = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})

    assert result == [{"text": "喷火龙", "score": 0.97}]


def test_paddle_ocr_adapter_uses_pre_cropped_roi_frame_without_recropping(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    def fail_if_recrop(frame, roi):
        raise AssertionError("should not crop an already-cropped roi frame")

    monkeypatch.setattr(paddle_ocr_adapter, "build_roi_frame", fail_if_recrop)
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter(ocr_engine=StubOcrEngine())
    result = adapter.read_text(
        {
            "width": 48,
            "height": 32,
            "preview_image_data_url": "data:image/jpeg;base64,stub",
            "source_preview_image_data_url": "data:image/jpeg;base64,source-stub",
            "pixel_box": {"left": 10, "top": 20, "width": 48, "height": 32},
        },
        {"x": 0.7, "y": 0.42, "w": 0.24, "h": 0.32},
    )

    assert result == [{"text": "喷火龙", "score": 0.97}]


def test_paddle_ocr_adapter_accepts_injected_engine():
    """Adapter can be constructed with a pre-built engine (for testing)."""
    adapter = PaddleOcrAdapter(ocr_engine=StubOcrEngine())
    assert isinstance(adapter._ocr_engine, StubOcrEngine)


def test_paddle_ocr_adapter_handles_none_ocr_result(monkeypatch):
    """When RapidOCR returns None (no text detected), adapter returns empty list."""
    from app.services.recognizers import paddle_ocr_adapter

    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    class NoResultEngine:
        def __call__(self, image):
            return None, None

    adapter = PaddleOcrAdapter(ocr_engine=NoResultEngine())
    result = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})

    assert result == []
