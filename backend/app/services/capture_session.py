from __future__ import annotations

import base64
import importlib
import re
import shutil
import subprocess
import threading
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
            preview_image_data_url = encode_preview_image(frame)
            phase_preview_image_data_url = encode_preview_image(frame, max_width=640)
            phase_width = 640 if width > 640 else int(width)
            phase_height = max(1, int(round(height * (phase_width / width)))) if width else int(height)
            return True, {
                'source_id': source['id'],
                'width': int(width),
                'height': int(height),
                'preview_image_data_url': preview_image_data_url,
                'capture_method': 'opencv',
                'capture_backend': str(source.get('backend') or 'opencv'),
                'frame_variants': {
                    'phase_frame': {
                        'width': phase_width,
                        'height': phase_height,
                        'preview_image_data_url': phase_preview_image_data_url or preview_image_data_url,
                    },
                    'roi_source_frame': {
                        'width': int(width),
                        'height': int(height),
                        'preview_image_data_url': preview_image_data_url,
                    },
                },
            }
        finally:
            if capture is not None:
                capture.release()

    def _read_with_ffmpeg_dshow(self, source: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        ffmpeg_path = self._ffmpeg_resolver()
        if ffmpeg_path is None:
            return False, {'source_id': source['id'], 'error': 'ffmpeg_not_found'}

        command = self._build_ffmpeg_dshow_capture_command(ffmpeg_path, source['capture_selector'])
        try:
            result = self._ffmpeg_runner(command)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return False, {'source_id': source['id'], 'error': 'ffmpeg_open_failed'}

        stdout = getattr(result, 'stdout', b'') or b''
        stderr = decode_ffmpeg_output(getattr(result, 'stderr', b'') or b'')
        returncode = int(getattr(result, 'returncode', 0) or 0)
        if returncode == 0 and stdout:
            return True, {
                'source_id': source['id'],
                'preview_image_data_url': 'data:image/jpeg;base64,' + base64.b64encode(stdout).decode('ascii'),
                'capture_method': 'ffmpeg-dshow',
                'capture_backend': 'dshow',
            }

        for option in self._probe_ffmpeg_dshow_options(ffmpeg_path, source['capture_selector']):
            retry_command = self._build_ffmpeg_dshow_capture_command(
                ffmpeg_path,
                source['capture_selector'],
                video_size=option.get('video_size'),
                framerate=option.get('framerate'),
            )
            try:
                retry_result = self._ffmpeg_runner(retry_command)
            except (FileNotFoundError, OSError, subprocess.SubprocessError):
                continue

            retry_stdout = getattr(retry_result, 'stdout', b'') or b''
            retry_stderr = decode_ffmpeg_output(getattr(retry_result, 'stderr', b'') or b'')
            retry_returncode = int(getattr(retry_result, 'returncode', 0) or 0)
            if retry_returncode == 0 and retry_stdout:
                payload = {
                    'source_id': source['id'],
                    'preview_image_data_url': 'data:image/jpeg;base64,' + base64.b64encode(retry_stdout).decode('ascii'),
                    'capture_method': 'ffmpeg-dshow',
                    'capture_backend': 'dshow',
                }
                if option.get('video_size'):
                    payload['capture_video_size'] = option['video_size']
                if option.get('framerate'):
                    payload['capture_framerate'] = option['framerate']
                return True, payload
            if retry_stderr:
                stderr = retry_stderr

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

    def _build_ffmpeg_dshow_capture_command(
        self,
        ffmpeg_path: str,
        capture_selector: str,
        *,
        video_size: str | None = None,
        framerate: str | None = None,
    ) -> list[str]:
        command = [
            ffmpeg_path,
            '-hide_banner',
            '-loglevel',
            'error',
            '-f',
            'dshow',
            '-rtbufsize',
            '256M',
        ]
        if video_size:
            command.extend(['-video_size', video_size])
        if framerate:
            command.extend(['-framerate', framerate])
        command.extend([
            '-i',
            f'video={capture_selector}',
            '-frames:v',
            '1',
            '-f',
            'image2pipe',
            '-vcodec',
            'mjpeg',
            '-',
        ])
        return command

    def _probe_ffmpeg_dshow_options(self, ffmpeg_path: str, capture_selector: str) -> list[dict[str, str]]:
        command = [
            ffmpeg_path,
            '-hide_banner',
            '-f',
            'dshow',
            '-list_options',
            'true',
            '-i',
            f'video={capture_selector}',
        ]
        try:
            result = self._ffmpeg_runner(command)
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return []

        stderr = decode_ffmpeg_output(getattr(result, 'stderr', b'') or b'')
        options = self._parse_ffmpeg_dshow_options(stderr)
        return options[:3]

    def _parse_ffmpeg_dshow_options(self, output: str) -> list[dict[str, str]]:
        if not output:
            return []

        options: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for line in output.splitlines():
            size_match = re.search(r's=(\d+x\d+)', line)
            fps_match = re.search(r'fps=(\d+(?:\.\d+)?)', line)
            if not size_match:
                continue
            video_size = size_match.group(1)
            framerate = fps_match.group(1) if fps_match else '30'
            key = (video_size, framerate)
            if key in seen:
                continue
            seen.add(key)
            options.append({'video_size': video_size, 'framerate': framerate})
        return options

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


def encode_preview_image(frame: Any, *, max_width: int = 1280) -> str | None:
    if cv2 is None or frame is None:
        return None

    preview = frame
    height, width = preview.shape[:2]
    if width > max_width:
        scale = max_width / width
        preview = cv2.resize(preview, (int(width * scale), int(height * scale)))

    ok, encoded = cv2.imencode('.jpg', preview, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
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


def build_frame_variants(frame_metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    width = frame_metadata.get('width')
    height = frame_metadata.get('height')
    preview_image_data_url = frame_metadata.get('preview_image_data_url')

    phase_width = width
    phase_height = height
    if isinstance(width, int) and isinstance(height, int) and width > 1280:
        phase_width = 1280
        phase_height = max(1, int(round(height * (1280 / width))))

    return {
        'phase_frame': {
            'width': phase_width,
            'height': phase_height,
            'preview_image_data_url': preview_image_data_url,
        },
        'roi_source_frame': {
            'width': width,
            'height': height,
            'preview_image_data_url': preview_image_data_url,
        },
    }


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
    """Service that owns the capture loop with a dedicated background thread.

    On start(), launches a CaptureThread that captures at ``interval_seconds``
    intervals and writes each result into FrameStore.  poll() / get_state()
    are now cheap reads — they never trigger a capture.
    """

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
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self, source_id: str | dict[str, Any]) -> dict[str, Any]:
        source = normalize_capture_source(source_id)
        self._running = True
        self._source = source
        self._source_id = source['id']
        # Initial capture so the first state is non-empty
        self._capture_once()
        # Launch background capture thread
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop,
            name='capture-loop',
            daemon=True,
        )
        self._thread.start()
        return self.get_state()

    def stop(self) -> dict[str, Any]:
        self._running = False
        self._stop_event.set()
        self._thread = None
        return self.get_state()

    def poll(self) -> dict[str, Any]:
        # poll() no longer triggers capture — the background thread handles it.
        return self.get_state()

    def get_state(self) -> dict[str, Any]:
        return {
            'running': self._running,
            'source_id': self._source_id,
            'interval_seconds': self._interval_seconds,
            'latest_frame': self._frame_store.get_latest_frame(),
        }

    def _capture_loop(self) -> None:
        """Background thread: capture at interval_seconds until stopped."""
        while not self._stop_event.is_set():
            now = self._now_fn()
            if self._last_capture_at is None or (now - self._last_capture_at) >= self._interval_seconds:
                self._capture_once()
            # Sleep a short while then loop (avoids busy-wait while keeping
            # responsiveness to stop events).
            self._stop_event.wait(max(0.05, self._interval_seconds / 2))

    def _capture_once(self) -> None:
        assert self._source_id is not None
        capture_target = self._source if isinstance(self._capture_reader, OpenCVCaptureReader) else self._source_id
        ok, frame_payload = self._capture_reader.read(capture_target)
        frame_metadata = dict(frame_payload)
        frame_metadata.setdefault('source_id', self._source_id)
        frame_metadata.setdefault('captured_at', self._now_fn())

        if not ok:
            frame_metadata.setdefault('preview_image_data_url', black_preview_image_data_url())
            frame_metadata.setdefault('frame_variants', build_frame_variants(frame_metadata))
            self._frame_store.set_latest_frame(frame_metadata)
            self._last_capture_at = self._now_fn()
            return

        frame_metadata.setdefault('frame_variants', build_frame_variants(frame_metadata))
        self._frame_store.set_latest_frame(frame_metadata)
        self._last_capture_at = self._now_fn()
