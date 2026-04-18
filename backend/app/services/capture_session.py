from __future__ import annotations

import base64
from typing import Any, Callable

from app.core.settings import get_settings
from app.services.frame_store import FrameStore

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class OpenCVCaptureReader:
    def read(self, source_id: str) -> tuple[bool, dict[str, Any]]:
        if cv2 is None:
            return False, {"source_id": source_id, "error": "opencv_not_installed"}

        source = int(source_id) if str(source_id).isdigit() else source_id
        capture = None
        try:
            if hasattr(cv2, "CAP_DSHOW"):
                capture = cv2.VideoCapture(source, cv2.CAP_DSHOW)
                if capture is None or not capture.isOpened():
                    if capture is not None:
                        capture.release()
                    capture = cv2.VideoCapture(source)
            else:
                capture = cv2.VideoCapture(source)

            if capture is None or not capture.isOpened():
                return False, {"source_id": source_id, "error": "open_failed"}

            ok, frame = capture.read()
            if not ok or frame is None:
                return False, {"source_id": source_id, "error": "read_failed"}

            height, width = frame.shape[:2]
            return True, {
                "source_id": source_id,
                "width": int(width),
                "height": int(height),
                "preview_image_data_url": encode_preview_image(frame),
            }
        finally:
            if capture is not None:
                capture.release()


def encode_preview_image(frame: Any) -> str | None:
    if cv2 is None or frame is None:
        return None

    preview = frame
    height, width = preview.shape[:2]
    max_width = 640
    if width > max_width:
        scale = max_width / width
        preview = cv2.resize(preview, (int(width * scale), int(height * scale)))

    ok, encoded = cv2.imencode('.jpg', preview, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return None
    return 'data:image/jpeg;base64,' + base64.b64encode(encoded.tobytes()).decode('ascii')


def black_preview_image_data_url() -> str:
    return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAwMBAS8QJZkAAAAASUVORK5CYII='


class CaptureSessionService:
    def __init__(
        self,
        frame_store: FrameStore | None = None,
        capture_reader: Any | None = None,
        now_fn: Callable[[], float] | None = None,
    ) -> None:
        self._frame_store = frame_store or FrameStore()
        self._capture_reader = capture_reader or OpenCVCaptureReader()
        self._now_fn = now_fn or __import__('time').time
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
            'running': self._running,
            'source_id': self._source_id,
            'interval_seconds': self._interval_seconds,
            'latest_frame': self._frame_store.get_latest_frame(),
        }

    def _capture_once(self) -> None:
        assert self._source_id is not None
        ok, frame_payload = self._capture_reader.read(self._source_id)
        frame_metadata = dict(frame_payload)
        frame_metadata.setdefault('source_id', self._source_id)
        frame_metadata.setdefault('captured_at', self._now_fn())

        if not ok:
            frame_metadata.setdefault('preview_image_data_url', black_preview_image_data_url())
            self._frame_store.set_latest_frame(frame_metadata)
            self._last_capture_at = self._now_fn()
            return

        self._frame_store.set_latest_frame(frame_metadata)
        self._last_capture_at = self._now_fn()
