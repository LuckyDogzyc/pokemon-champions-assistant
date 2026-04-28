from __future__ import annotations

from dataclasses import dataclass

from app.core.settings import Settings, get_settings
from app.services.recognition_pipeline import RecognitionPipeline
from app.services.recognizers.chinese_ocr_recognizer import ChineseOcrSideRecognizer
from app.services.recognizers.mock_recognizer import MockSideRecognizer
from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter


MOCK_PROVIDER_WARNING = "当前仍在使用 mock OCR provider，ROI 截图可见但不会产出真实识别文本。"


@dataclass(frozen=True)
class RecognitionRuntime:
    pipeline: RecognitionPipeline
    active_provider: str
    warning: str | None = None


def create_recognition_runtime(settings: Settings | None = None) -> RecognitionRuntime:
    resolved_settings = settings or get_settings()
    provider = str(resolved_settings.ocr_provider or "mock").strip().lower() or "mock"

    if provider == "mock":
        return RecognitionRuntime(
            pipeline=RecognitionPipeline(recognizer=MockSideRecognizer()),
            active_provider="mock",
            warning=MOCK_PROVIDER_WARNING,
        )

    if provider == "paddleocr":
        try:
            recognizer = ChineseOcrSideRecognizer(ocr_adapter=PaddleOcrAdapter())
        except ImportError as exc:
            return RecognitionRuntime(
                pipeline=RecognitionPipeline(recognizer=MockSideRecognizer()),
                active_provider="mock",
                warning=(
                    "已配置 paddleocr，但 RapidOCR 导入失败或依赖不可用"
                    f"（{exc}），已回退到 mock OCR provider。"
                ),
            )
        return RecognitionRuntime(
            pipeline=RecognitionPipeline(recognizer=recognizer),
            active_provider="paddleocr",
            warning=None,
        )

    return RecognitionRuntime(
        pipeline=RecognitionPipeline(recognizer=MockSideRecognizer()),
        active_provider="mock",
        warning=f"未识别的 OCR provider: {provider}，已回退到 mock OCR provider。",
    )
