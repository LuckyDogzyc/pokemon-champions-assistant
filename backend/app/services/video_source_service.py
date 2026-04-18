from __future__ import annotations

import importlib
import re
import shutil
import subprocess
import sys
from collections.abc import Callable

from app.schemas.video import VideoSource

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class VideoSourceService:
    def __init__(
        self,
        max_devices: int = 12,
        *,
        ffmpeg_runner: Callable[[list[str]], object] | None = None,
        platform: str | None = None,
    ) -> None:
        self._max_devices = max_devices
        self._ffmpeg_runner = ffmpeg_runner or self._run_ffmpeg_command
        self._platform = platform or sys.platform

    def list_sources(self) -> list[VideoSource]:
        detected = self._detect_with_opencv()
        if detected:
            return self._apply_friendly_labels(detected, self._get_windows_friendly_labels())
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

    def _get_windows_friendly_labels(self) -> list[str]:
        if self._platform != "win32":
            return []
        ffmpeg_path = self._resolve_ffmpeg_executable()
        if ffmpeg_path is None:
            return []

        command = [ffmpeg_path, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"]
        try:
            result = self._ffmpeg_runner(command)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return []

        stderr = self._decode_ffmpeg_output(getattr(result, "stderr", "") or "")
        return self._parse_dshow_video_device_names(stderr)

    def _resolve_ffmpeg_executable(self) -> str | None:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        try:
            imageio_ffmpeg = importlib.import_module("imageio_ffmpeg")
        except ImportError:
            return None

        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:  # pragma: no cover - defensive fallback for third-party package quirks
            return None

    def _run_ffmpeg_command(self, command: list[str]):
        return subprocess.run(command, capture_output=True, text=False, check=False)

    def _decode_ffmpeg_output(self, output: bytes | str) -> str:
        if isinstance(output, str):
            return output

        for encoding in ("utf-8", "utf-8-sig", "gbk", "cp936"):
            try:
                return output.decode(encoding)
            except UnicodeDecodeError:
                continue

        return output.decode("utf-8", errors="replace")

    def _parse_dshow_video_device_names(self, output: str) -> list[str]:
        if not output:
            return []

        labels: list[str] = []
        inside_video_section = False

        for raw_line in output.splitlines():
            line = raw_line.strip()
            lower_line = line.lower()

            if "directshow video devices" in lower_line:
                inside_video_section = True
                continue
            if inside_video_section and "directshow audio devices" in lower_line:
                break
            if not inside_video_section or "alternative name" in lower_line:
                continue

            match = re.search(r'"([^"]+)"', line)
            if match:
                labels.append(match.group(1))

        return labels

    def _apply_friendly_labels(self, sources: list[VideoSource], labels: list[str]) -> list[VideoSource]:
        if not labels:
            return sources

        updated_sources: list[VideoSource] = []
        for order_index, source in enumerate(sources):
            index = source.device_index
            friendly_label = None

            if index is not None and 0 <= index < len(labels):
                friendly_label = labels[index]
            elif order_index < len(labels):
                friendly_label = labels[order_index]

            if friendly_label is None:
                updated_sources.append(source)
                continue

            updated_sources.append(
                source.model_copy(
                    update={
                        "label": friendly_label,
                        "is_capture_card_candidate": source.is_capture_card_candidate
                        or self._looks_like_capture_card(friendly_label),
                    }
                )
            )
        return updated_sources

    def _looks_like_capture_card(self, label: str) -> bool:
        normalized = label.lower()
        capture_keywords = (
            "capture",
            "cam link",
            "elgato",
            "hdmi",
            "usb video",
            "uvc",
        )
        return any(keyword in normalized for keyword in capture_keywords)
