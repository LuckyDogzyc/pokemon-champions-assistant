from app.core.settings import Settings
from app.services.recognition_runtime import create_recognition_runtime
from app.services.recognizers.chinese_ocr_recognizer import ChineseOcrSideRecognizer
from app.services.recognizers.mock_recognizer import MockSideRecognizer


class StubPaddleOcrAdapter:
    def __init__(self):
        self.created = True


def test_create_recognition_runtime_prefers_paddleocr_by_default(monkeypatch):
    from app.services import recognition_runtime

    monkeypatch.setattr(recognition_runtime, "PaddleOcrAdapter", StubPaddleOcrAdapter)

    runtime = create_recognition_runtime(Settings())

    assert isinstance(runtime.pipeline._recognizer, ChineseOcrSideRecognizer)
    assert isinstance(runtime.pipeline._recognizer._ocr_adapter, StubPaddleOcrAdapter)
    assert runtime.active_provider == "paddleocr"
    assert runtime.warning is None


def test_create_recognition_runtime_uses_paddleocr_recognizer(monkeypatch):
    from app.services import recognition_runtime

    monkeypatch.setattr(recognition_runtime, "PaddleOcrAdapter", StubPaddleOcrAdapter)

    runtime = create_recognition_runtime(Settings(ocr_provider="paddleocr"))

    assert isinstance(runtime.pipeline._recognizer, ChineseOcrSideRecognizer)
    assert isinstance(runtime.pipeline._recognizer._ocr_adapter, StubPaddleOcrAdapter)
    assert runtime.active_provider == "paddleocr"
    assert runtime.warning is None


def test_create_recognition_runtime_falls_back_when_paddleocr_unavailable(monkeypatch):
    from app.services import recognition_runtime

    class MissingPaddleOcrAdapter:
        def __init__(self):
            raise ImportError("paddleocr is not installed")

    monkeypatch.setattr(recognition_runtime, "PaddleOcrAdapter", MissingPaddleOcrAdapter)

    runtime = create_recognition_runtime(Settings(ocr_provider="paddleocr"))

    assert isinstance(runtime.pipeline._recognizer, MockSideRecognizer)
    assert runtime.active_provider == "mock"
    assert "paddleocr" in (runtime.warning or "")
    assert "回退" in (runtime.warning or "")
    assert "导入失败" in (runtime.warning or "")
    assert "依赖不可用" in (runtime.warning or "")
    assert "初始化失败" not in (runtime.warning or "")
    assert "未安装 paddleocr" not in (runtime.warning or "")


def test_create_recognition_runtime_falls_back_when_provider_unknown():
    runtime = create_recognition_runtime(Settings(ocr_provider="something-else"))

    assert isinstance(runtime.pipeline._recognizer, MockSideRecognizer)
    assert runtime.active_provider == "mock"
    assert "something-else" in (runtime.warning or "")
