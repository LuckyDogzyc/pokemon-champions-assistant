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
        windows_device_enumerator: Callable[[], list[str]] | None = None,
    ) -> None:
        self._max_devices = max_devices
        self._ffmpeg_runner = ffmpeg_runner or self._run_ffmpeg_command
        self._platform = platform or sys.platform
        self._windows_device_enumerator = windows_device_enumerator or self._enumerate_windows_devices

    def list_sources(self) -> list[VideoSource]:
        if self._platform == 'win32':
            windows_sources = self._list_windows_sources()
            if windows_sources:
                return windows_sources
            return [
                VideoSource(
                    id='0',
                    label='Default Camera / Capture Device',
                    backend='opencv',
                    is_capture_card_candidate=True,
                    device_index=0,
                    capture_selector='0',
                    device_kind='unknown',
                )
            ]

        detected = self._detect_with_opencv()
        if detected:
            return detected
        return [
            VideoSource(
                id='0',
                label='Default Camera / Capture Device',
                backend='opencv',
                is_capture_card_candidate=True,
                device_index=0,
                capture_selector='0',
                device_kind='unknown',
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
            label = f'Video Device {index}'
            sources.append(
                VideoSource(
                    id=str(index),
                    label=label,
                    backend='opencv',
                    is_capture_card_candidate='capture' in label.lower() or index == 0,
                    device_index=index,
                    capture_selector=str(index),
                    device_kind=self._classify_device_kind(label),
                )
            )
            capture.release()
        return sources

    def _list_windows_sources(self) -> list[VideoSource]:
        labels = self._windows_device_enumerator()
        if labels:
            return self._build_windows_sources(labels)

        ffmpeg_labels = self._get_windows_friendly_labels()
        if ffmpeg_labels:
            return self._build_windows_sources(ffmpeg_labels)

        return []

    def _build_windows_sources(self, labels: list[str]) -> list[VideoSource]:
        sources: list[VideoSource] = []
        for index, label in enumerate(labels):
            sources.append(
                VideoSource(
                    id=str(index),
                    label=label,
                    backend='dshow',
                    is_capture_card_candidate=self._looks_like_capture_card(label) or index == 0,
                    device_index=index,
                    capture_selector=label,
                    device_kind=self._classify_device_kind(label),
                )
            )
        return sources

    def _enumerate_windows_devices(self) -> list[str]:
        if self._platform != 'win32':
            return []

        try:
            dshow_graph = importlib.import_module('pygrabber.dshow_graph')
        except ImportError:
            return []

        filter_graph_cls = getattr(dshow_graph, 'FilterGraph', None)
        if filter_graph_cls is None:
            return []

        try:
            filter_graph = filter_graph_cls()
            devices = filter_graph.get_input_devices()
        except Exception:
            return []

        return [str(device).strip() for device in devices if str(device).strip()]

    def _open_capture(self, index: int):
        if cv2 is None:
            return None
        if hasattr(cv2, 'CAP_DSHOW'):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture is not None and capture.isOpened():
                return capture
            if capture is not None:
                capture.release()
        return cv2.VideoCapture(index)

    def _get_windows_friendly_labels(self) -> list[str]:
        if self._platform != 'win32':
            return []
        ffmpeg_path = self._resolve_ffmpeg_executable()
        if ffmpeg_path is None:
            return []

        command = [ffmpeg_path, '-hide_banner', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
        try:
            result = self._ffmpeg_runner(command)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return []

        stderr = self._decode_ffmpeg_output(getattr(result, 'stderr', '') or '')
        return self._parse_dshow_video_device_names(stderr)

    def _resolve_ffmpeg_executable(self) -> str | None:
        system_ffmpeg = shutil.which('ffmpeg')
        if system_ffmpeg:
            return system_ffmpeg

        try:
            imageio_ffmpeg = importlib.import_module('imageio_ffmpeg')
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

        for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'cp936'):
            try:
                return output.decode(encoding)
            except UnicodeDecodeError:
                continue

        return output.decode('utf-8', errors='replace')

    def _parse_dshow_video_device_names(self, output: str) -> list[str]:
        if not output:
            return []

        labels: list[str] = []
        inside_video_section = False

        for raw_line in output.splitlines():
            line = raw_line.strip()
            lower_line = line.lower()

            if 'directshow video devices' in lower_line:
                inside_video_section = True
                continue
            if inside_video_section and 'directshow audio devices' in lower_line:
                break
            if not inside_video_section or 'alternative name' in lower_line:
                continue

            match = re.search(r'"([^"]+)"', line)
            if match:
                labels.append(match.group(1))

        return labels

    def _looks_like_capture_card(self, label: str) -> bool:
        normalized = label.lower()
        capture_keywords = (
            'capture',
            'cam link',
            'elgato',
            'hdmi',
            'usb video',
            'uvc',
        )
        return any(keyword in normalized for keyword in capture_keywords)

    def _classify_device_kind(self, label: str) -> str:
        normalized = label.lower()
        virtual_keywords = (
            'virtual',
            'obs',
            'broadcast',
            'manycam',
            'snap camera',
            'xsplit',
            'vcam',
        )
        if any(keyword in normalized for keyword in virtual_keywords):
            return 'virtual'
        return 'physical'
