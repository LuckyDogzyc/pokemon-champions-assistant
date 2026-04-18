from __future__ import annotations

import base64
import importlib
import shutil
import subprocess
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from app.core.settings import get_settings
from app.services.frame_store import FrameStore

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class OpenCVCaptureReader:
    def __init__(
        self,
        *,
        ffmpeg_runner: Callable[[list[str]], Any] | None = None,
        ffmpeg_resolver: Callable[[], str | None] | None = None,
    ) -> None:
        self._ffmpeg_runner = ffmpeg_runner or self._run_ffmpeg_command
        self._ffmpeg_resolver = ffmpeg_resolver or self._resolve_ffmpeg_executable

    def read(self, source_id: str | dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        source = normalize_capture_source(source_id)
        if source.get('backend') == 'dshow' and source.get('capture_selector'):
            return self._read_with_ffmpeg_dshow(source)

        return self._read_with_opencv(source)

    def _read_with_opencv(self, source: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        if cv2 is None:
            return False, {
                'source_id': source['id'],
                'error': 'opencv_not_installed',
                'capture_method': 'opencv',
                'capture_backend': str(source.get('backend') or 'opencv'),
            }

        capture_target = self._resolve_opencv_capture_target(source)
        capture = None
        try:
            if hasattr(cv2, 'CAP_DSHOW'):
                capture = cv2.VideoCapture(capture_target, cv2.CAP_DSHOW)
                if capture is None or not capture.isOpened():
                    if capture is not None:
                        capture.release()
                    capture = cv2.VideoCapture(capture_target)
            else:
                capture = cv2.VideoCapture(capture_target)

            if capture is None or not capture.isOpened():
                return False, {
                    'source_id': source['id'],
                    'error': 'open_failed',
                    'capture_method': 'opencv',
                    'capture_backend': str(source.get('backend') or 'opencv'),
                }

            ok, frame = capture.read()
            if not ok or frame is None:
                return False, {
                    'source_id': source['id'],
                    'error': 'read_failed',
                    'capture_method': 'opencv',
                    'capture_backend': str(source.get('backend') or 'opencv'),
                }

            height, width = frame.shape[:2]
            return True, {
                'source_id': source['id'],
                'width': int(width),
                'height': int(height),
                'preview_image_data_url': encode_preview_image(frame),
                'capture_method': 'opencv',
            }
        finally:
            if capture is not None:
                capture.release()

    def _read_with_ffmpeg_dshow(self, source: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        ffmpeg_path = self._ffmpeg_resolver()
        if ffmpeg_path is None:
            return False, {'source_id': source['id'], 'error': 'ffmpeg_not_found'}

        command = [
            ffmpeg_path,
            '-hide_banner',
            '-loglevel',
            'error',
            '-f',
            'dshow',
            '-i',
            f"video={source['capture_selector']}",
            '-frames:v',
            '1',
            '-f',
            'image2pipe',
            '-vcodec',
            'mjpeg',
            '-',
        ]
        try:
            result = self._ffmpeg_runner(command)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return False, {'source_id': source['id'], 'error': 'ffmpeg_open_failed'}

        stdout = getattr(result, 'stdout', b'') or b''
        stderr = decode_ffmpeg_output(getattr(result, 'stderr', b'') or b'')
        returncode = int(getattr(result, 'returncode', 0) or 0)
        if returncode != 0 or not stdout:
            return False, {
                'source_id': source['id'],
                'error': 'ffmpeg_read_failed',
                'error_detail': stderr or None,
                'capture_method': 'ffmpeg-dshow',
                'capture_backend': 'dshow',
            }

        return True, {
            'source_id': source['id'],
            'preview_image_data_url': 'data:image/jpeg;base64,' + base64.b64encode(stdout).decode('ascii'),
            'capture_method': 'ffmpeg-dshow',
            'capture_backend': 'dshow',
        }

    def _resolve_opencv_capture_target(self, source: dict[str, Any]) -> Any:
        device_index = source.get('device_index')
        if device_index is not None:
            return int(device_index)
        capture_selector = source.get('capture_selector')
        if capture_selector is not None and str(capture_selector).isdigit():
            return int(capture_selector)
        source_id = source.get('id')
        return int(source_id) if str(source_id).isdigit() else source_id

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
        except Exception:  # pragma: no cover
            return None

    def _run_ffmpeg_command(self, command: list[str]) -> Any:
        return subprocess.run(command, capture_output=True, text=False, check=False)


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
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<rect width="640" height="360" fill="#000000"/>'
        '<text x="50%" y="50%" fill="#aaaaaa" font-size="24" text-anchor="middle" dominant-baseline="middle">'
        '当前输入源抓帧失败'
        '</text>'
        '</svg>'
    )
    return 'data:image/svg+xml;utf8,' + quote(svg)


def normalize_capture_source(source: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        normalized = dict(source)
        normalized.setdefault('id', str(source.get('id') or source.get('source_id') or '0'))
        normalized.setdefault('backend', source.get('backend') or 'opencv')
        normalized.setdefault('capture_selector', source.get('capture_selector'))
        normalized.setdefault('device_index', source.get('device_index'))
        return normalized

    return {
        'id': str(source),
        'backend': 'opencv',
        'capture_selector': str(source),
        'device_index': int(source) if str(source).isdigit() else None,
    }


def decode_ffmpeg_output(output: bytes | str) -> str:
    if isinstance(output, str):
        return output

    for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'cp936'):
        try:
            return output.decode(encoding)
        except UnicodeDecodeError:
            continue

    return output.decode('utf-8', errors='replace')


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
        self._source: dict[str, Any] | None = None
        self._interval_seconds = get_settings().frame_interval_seconds
        self._last_capture_at: float | None = None

    def start(self, source_id: str | dict[str, Any]) -> dict[str, Any]:
        source = normalize_capture_source(source_id)
        self._running = True
        self._source = source
        self._source_id = source['id']
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
        capture_target = self._source if isinstance(self._capture_reader, OpenCVCaptureReader) else self._source_id
        ok, frame_payload = self._capture_reader.read(capture_target)
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
