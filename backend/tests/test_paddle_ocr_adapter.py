import pytest

from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter, _normalize_paddle_result

# Skip the entire module when OCR optional deps are not installed.
# These tests exercise ONNX-specific logic that requires onnxruntime + paddle2onnx.
pytest.importorskip("onnxruntime", reason="onnxruntime not installed")
pytest.importorskip("paddle2onnx", reason="paddle2onnx not installed")


class StubOcrEngine:
    def ocr(self, image, cls=False):
        return [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("喷火龙", 0.97)]]


class StubPaddleOcrClass:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _make_paddleocr_module(cls):
    """Create a fake paddleocr module with the given PaddleOCR class."""
    return type("FakePaddleOcrModule", (), {"PaddleOCR": cls})


def test_normalize_paddle_result_with_standard_output():
    normalized = _normalize_paddle_result([[[[0, 0], [1, 0], [1, 1], [0, 1]], ("皮卡丘", 0.88)]])

    assert normalized == [{"text": "皮卡丘", "score": 0.88}]


def test_paddle_ocr_adapter_uses_onnx_when_available(monkeypatch):
    """Adapter should initialize with use_onnx=True and CPUExecutionProvider."""
    from app.services.recognizers import paddle_ocr_adapter

    onnx_kwargs = {
        "det_model_dir": "/fake/det/inference.onnx",
        "rec_model_dir": "/fake/rec/inference.onnx",
    }

    captured_kwargs = {}

    class OnnxCapturingClass:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    def fake_import_module(name: str):
        assert name == "paddleocr"
        return _make_paddleocr_module(OnnxCapturingClass)

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(paddle_ocr_adapter, "_ensure_onnx_models", lambda: onnx_kwargs)

    adapter = PaddleOcrAdapter()

    assert captured_kwargs["use_onnx"] is True
    assert captured_kwargs["det_model_dir"] == "/fake/det/inference.onnx"
    assert captured_kwargs["rec_model_dir"] == "/fake/rec/inference.onnx"
    assert captured_kwargs["onnx_providers"] == ["CPUExecutionProvider"]


def test_paddle_ocr_adapter_raises_when_onnxruntime_missing(monkeypatch):
    """If onnxruntime is not importable, adapter should raise ImportError."""
    from app.services.recognizers import paddle_ocr_adapter
    import builtins
    import sys

    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "onnxruntime":
            raise ImportError("no module named 'onnxruntime'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    sys.modules.pop("onnxruntime", None)

    try:
        PaddleOcrAdapter()
        raise AssertionError("expected ImportError when onnxruntime is missing")
    except ImportError as exc:
        assert "onnxruntime" in str(exc).lower()


def test_paddle_ocr_adapter_raises_when_paddle2onnx_missing(monkeypatch):
    """If paddle2onnx is not installed, _ensure_onnx_models should raise ImportError."""
    from app.services.recognizers import paddle_ocr_adapter
    import sys

    monkeypatch.setitem(sys.modules, "paddle2onnx", None)

    with pytest.raises(ImportError, match="paddle2onnx"):
        paddle_ocr_adapter._ensure_onnx_models()


def test_paddle_ocr_adapter_raises_when_no_paddle_models(monkeypatch, tmp_path):
    """If no Paddle model dirs exist, _ensure_onnx_models should raise FileNotFoundError."""
    from app.services.recognizers import paddle_ocr_adapter

    monkeypatch.setattr(paddle_ocr_adapter, "_paddle_model_base_dir", lambda: tmp_path / "nonexistent")

    with pytest.raises(FileNotFoundError, match="No PaddleOCR"):
        paddle_ocr_adapter._ensure_onnx_models()


def test_paddle_ocr_adapter_wraps_non_import_import_failures(monkeypatch):
    """paddleocr module import failure should be wrapped in ImportError."""
    from app.services.recognizers import paddle_ocr_adapter

    # onnxruntime is available in this env, so the onnxruntime import succeeds;
    # but _load_paddle_ocr_class hits FileNotFoundError → should be wrapped.
    def fake_import_module(name: str):
        assert name == "paddleocr"
        raise FileNotFoundError("Cython/Utility/CppSupport.cpp")

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)

    with pytest.raises(ImportError, match="paddleocr import failed"):
        PaddleOcrAdapter()


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
