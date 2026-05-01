from __future__ import annotations

import threading
from dataclasses import dataclass

from app.core.settings import Settings, get_settings
from app.services.battle_state_store import BattleStateStore
from app.services.frame_store import FrameStore
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


class RecognizeScheduler:
    """Background thread that runs recognition at a fixed interval.

    Each cycle:
      1. Read the latest frame from FrameStore
      2. Run RecognitionPipeline.recognize(latest_frame)
      3. Update BattleStateStore
      4. Write the result back via pipeline.set_current_state()

    Only the *latest* frame is processed — if recognition is still running
    when the next cycle fires, the previous attempt is discarded.
    """

    def __init__(
        self,
        pipeline: RecognitionPipeline,
        frame_store: FrameStore,
        battle_state_store: BattleStateStore,
        interval_seconds: float = 1.0,
    ) -> None:
        self._pipeline = pipeline
        self._frame_store = frame_store
        self._battle_state_store = battle_state_store
        self._interval_seconds = interval_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name='recognize-loop',
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        self._thread = None

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            latest_frame = self._frame_store.get_latest_frame()
            if latest_frame and latest_frame.get('error') is None:
                try:
                    result = self._pipeline.recognize(latest_frame)
                    self._pipeline.set_current_state(result)
                    self._battle_state_store.update_from_recognition(result)
                except Exception:  # pragma: no cover
                    # Recognition errors are silently absorbed — the pipeline
                    # already catches and stores them via _recognize_or_last_state
                    pass
            self._stop_event.wait(self._interval_seconds)
