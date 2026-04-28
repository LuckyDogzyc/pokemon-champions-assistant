from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter, _normalize_paddle_result


class StubOcrEngine:
    def ocr(self, image, cls=False):
        return [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("喷火龙", 0.97)]]


class StubPaddleOcrClass:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class RecoveringPaddleOcrClass:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = 0
        RecoveringPaddleOcrClass.instances.append(self)

    def ocr(self, image, cls=False):
        self.calls += 1
        if len(RecoveringPaddleOcrClass.instances) == 1:
            raise RuntimeError("OneDnnContext does not have the input Filter")
        return [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("快龙", 0.93)]]


class AlwaysFailingRecoverablePaddleOcrClass:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = 0
        AlwaysFailingRecoverablePaddleOcrClass.instances.append(self)

    def ocr(self, image, cls=False):
        self.calls += 1
        raise RuntimeError("OneDnnContext does not have the input Filter; fused_conv2d predictor.run")


def test_normalize_paddle_result_with_standard_output():
    normalized = _normalize_paddle_result([[[[0, 0], [1, 0], [1, 1], [0, 1]], ("皮卡丘", 0.88)]])

    assert normalized == [{"text": "皮卡丘", "score": 0.88}]


def test_paddle_ocr_adapter_imports_paddleocr_lazily(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    def fake_import_module(name: str):
        assert name == "paddleocr"
        return type("FakePaddleOcrModule", (), {"PaddleOCR": StubPaddleOcrClass})

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)

    adapter = PaddleOcrAdapter()

    assert isinstance(adapter._ocr_engine, StubPaddleOcrClass)
    assert adapter._ocr_engine.kwargs == {
        "use_angle_cls": False, "lang": "ch", "cpu_threads": 1,
        "enable_mkldnn": False, "show_log": False,
    }


def test_paddle_ocr_adapter_wraps_non_import_import_failures(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    def fake_import_module(name: str):
        assert name == "paddleocr"
        raise FileNotFoundError("Cython/Utility/CppSupport.cpp")

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)

    try:
        PaddleOcrAdapter()
        raise AssertionError("expected PaddleOcrAdapter() to raise ImportError when paddleocr bootstrap is broken")
    except ImportError as exc:
        assert "paddleocr import failed" in str(exc)
        assert "CppSupport.cpp" in str(exc)


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


def test_paddle_ocr_adapter_recreates_engine_once_after_recoverable_runtime_error(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    RecoveringPaddleOcrClass.instances = []

    def fake_import_module(name: str):
        assert name == "paddleocr"
        return type("FakePaddleOcrModule", (), {"PaddleOCR": RecoveringPaddleOcrClass})

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter()
    result = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})

    assert result == [{"text": "快龙", "score": 0.93}]
    assert len(RecoveringPaddleOcrClass.instances) == 2
    assert RecoveringPaddleOcrClass.instances[0].calls == 1
    assert RecoveringPaddleOcrClass.instances[1].calls == 1


def test_paddle_ocr_adapter_returns_empty_texts_when_recovery_retry_also_fails(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    AlwaysFailingRecoverablePaddleOcrClass.instances = []

    def fake_import_module(name: str):
        assert name == "paddleocr"
        return type("FakePaddleOcrModule", (), {"PaddleOCR": AlwaysFailingRecoverablePaddleOcrClass})

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter()
    result = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})

    assert result == []
    assert len(AlwaysFailingRecoverablePaddleOcrClass.instances) == 2
    assert AlwaysFailingRecoverablePaddleOcrClass.instances[0].calls == 1
    assert AlwaysFailingRecoverablePaddleOcrClass.instances[1].calls == 1


def test_paddle_ocr_adapter_rebuild_cooldown_prevents_repeated_rebuild(monkeypatch):
    """Second call within cooldown should NOT rebuild the engine again."""
    from app.services.recognizers import paddle_ocr_adapter

    AlwaysFailingRecoverablePaddleOcrClass.instances = []

    def fake_import_module(name: str):
        assert name == "paddleocr"
        return type("FakePaddleOcrModule", (), {"PaddleOCR": AlwaysFailingRecoverablePaddleOcrClass})

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter()

    # First call: engine fails, rebuilds, still fails → returns [].
    # 2 instances created (original + rebuilt).
    result1 = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})
    assert result1 == []
    assert len(AlwaysFailingRecoverablePaddleOcrClass.instances) == 2

    # Second call (immediate, within cooldown): should NOT rebuild.
    # Still returns [] but no new instance created.
    result2 = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})
    assert result2 == []
    assert len(AlwaysFailingRecoverablePaddleOcrClass.instances) == 2  # no new rebuild


def test_paddle_ocr_adapter_rebuild_after_cooldown(monkeypatch):
    """After cooldown expires, engine should be rebuilt again."""
    from app.services.recognizers import paddle_ocr_adapter

    AlwaysFailingRecoverablePaddleOcrClass.instances = []

    def fake_import_module(name: str):
        assert name == "paddleocr"
        return type("FakePaddleOcrModule", (), {"PaddleOCR": AlwaysFailingRecoverablePaddleOcrClass})

    monkeypatch.setattr(paddle_ocr_adapter.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter()

    # First call triggers rebuild.
    adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})
    assert len(AlwaysFailingRecoverablePaddleOcrClass.instances) == 2

    # Simulate cooldown expiring.
    adapter._last_rebuild_time = 0.0

    # Now rebuild should be allowed again.
    adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})
    assert len(AlwaysFailingRecoverablePaddleOcrClass.instances) == 3


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
