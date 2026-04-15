from __future__ import annotations

from typing import Any, Callable

from app.core.settings import get_settings
from app.services.frame_store import FrameStore


class OpenCVCaptureReader:
    def read(self, source_id: str) -> tuple[bool, dict[str, Any]]:
        return True, {"source_id": source_id, "frame_no": 1}


class CaptureSessionService:
    def __init__(
        self,
        frame_store: FrameStore | None = None,
        capture_reader: Any | None = None,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self._frame_store = frame_store or FrameStore()
        self._capture_reader = capture_reader or OpenCVCaptureReader()
        self._now_fn = now_fn or __import__("time").time
        self._running = False
        self._source_id: str | None = None
        self._interval_seconds = get_settings().frame_interval_seconds
        self._last_capture_at: float | None = None

    def start(self, source_id: str) -> dict[str, Any]:
        self._running = True
        self._source_id = source_id
        self._capture_once()
        return self.get_state()

    def poll(self) -> dict[str, Any]:
        if self._running and self._last_capture_at is not None:
            elapsed = self._now_fn() - self._last_capture_at
            if elapsed >= self._interval_seconds:
                self._capture_once()
        return self.get_state()

    def stop(self) -> dict[str, Any]:
        self._running = False
        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "source_id": self._source_id,
            "interval_seconds": self._interval_seconds,
            "latest_frame": self._frame_store.get_latest_frame(),
        }

    def _capture_once(self) -> None:
        assert self._source_id is not None
        ok, frame_payload = self._capture_reader.read(self._source_id)
        if not ok:
            return
        frame_metadata = dict(frame_payload)
        frame_metadata.setdefault("source_id", self._source_id)
        frame_metadata.setdefault("captured_at", self._now_fn())
        self._frame_store.set_latest_frame(frame_metadata)
        self._last_capture_at = self._now_fn()
