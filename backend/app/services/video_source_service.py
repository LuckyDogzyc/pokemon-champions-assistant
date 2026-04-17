from __future__ import annotations

from app.schemas.video import VideoSource

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class VideoSourceService:
    def __init__(self, max_devices: int = 12) -> None:
        self._max_devices = max_devices

    def list_sources(self) -> list[VideoSource]:
        detected = self._detect_with_opencv()
        if detected:
            return detected
        return [
            VideoSource(
                id="0",
                label="Default Camera / Capture Device",
                backend="opencv",
                is_capture_card_candidate=True,
                device_index=0,
            )
        ]

    def _detect_with_opencv(self) -> list[VideoSource]:
        if cv2 is None:
            return []

        sources: list[VideoSource] = []
        for index in range(self._max_devices):
            capture = self._open_capture(index)
            if capture is None or not capture.isOpened():
                if capture is not None:
                    capture.release()
                continue
            label = f"Video Device {index}"
            sources.append(
                VideoSource(
                    id=str(index),
                    label=label,
                    backend="opencv",
                    is_capture_card_candidate="capture" in label.lower() or index == 0,
                    device_index=index,
                )
            )
            capture.release()
        return sources

    def _open_capture(self, index: int):
        if cv2 is None:
            return None
        if hasattr(cv2, "CAP_DSHOW"):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture is not None and capture.isOpened():
                return capture
            if capture is not None:
                capture.release()
        return cv2.VideoCapture(index)

