from __future__ import annotations

import base64
import binascii
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def build_pixel_box(frame: dict[str, Any], roi: dict[str, Any]) -> dict[str, int] | None:
    frame_width = int(frame.get('width') or 0)
    frame_height = int(frame.get('height') or 0)
    if frame_width <= 0 or frame_height <= 0:
        return None

    left = _scale_value(roi.get('x'), frame_width)
    top = _scale_value(roi.get('y'), frame_height)
    width = _scale_extent(roi.get('w'), frame_width)
    height = _scale_extent(roi.get('h'), frame_height)

    left = max(0, min(left, frame_width - 1))
    top = max(0, min(top, frame_height - 1))
    width = max(1, min(width, frame_width - left))
    height = max(1, min(height, frame_height - top))
    return {
        'left': left,
        'top': top,
        'width': width,
        'height': height,
    }


def build_roi_frame(frame: dict[str, Any], roi: dict[str, Any], *, ffmpeg_runner: Callable[..., Any] | None = None) -> dict[str, Any] | None:
    pixel_box = build_pixel_box(frame, roi)
    if pixel_box is None:
        return None

    cropped_preview = crop_preview_image_data_url(
        frame.get('preview_image_data_url'),
        pixel_box,
        ffmpeg_runner=ffmpeg_runner,
    )
    return {
        'width': pixel_box['width'],
        'height': pixel_box['height'],
        'pixel_box': pixel_box,
        'preview_image_data_url': cropped_preview,
        'source_preview_image_data_url': frame.get('preview_image_data_url'),
    }


def enrich_roi_payloads_with_crops(frame: dict[str, Any], roi_payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    enriched: dict[str, dict[str, Any]] = {}
    for name, payload in roi_payloads.items():
        next_payload = dict(payload)
        roi_frame = build_roi_frame(frame, next_payload)
        if roi_frame is not None:
            next_payload['pixel_box'] = roi_frame['pixel_box']
            next_payload['preview_image_data_url'] = roi_frame['preview_image_data_url']
            next_payload['crop_width'] = roi_frame['width']
            next_payload['crop_height'] = roi_frame['height']
        enriched[name] = next_payload
    return enriched


def crop_preview_image_data_url(
    preview_image_data_url: str | None,
    pixel_box: dict[str, int],
    *,
    ffmpeg_runner: Callable[..., Any] | None = None,
) -> str | None:
    if not preview_image_data_url:
        return None

    decoded = _decode_data_url(preview_image_data_url)
    if decoded is None:
        return None

    mime_type, image_bytes = decoded
    cropped_with_cv2 = _crop_preview_with_cv2(image_bytes, pixel_box)
    if cropped_with_cv2 is not None:
        return cropped_with_cv2

    input_codec = _mime_to_ffmpeg_codec(mime_type)
    ffmpeg_path = shutil.which('ffmpeg')
    if input_codec is None or ffmpeg_path is None:
        return None

    command = [
        ffmpeg_path,
        '-hide_banner',
        '-loglevel',
        'error',
        '-f',
        'image2pipe',
        '-vcodec',
        input_codec,
        '-i',
        'pipe:0',
        '-vf',
        f"crop={pixel_box['width']}:{pixel_box['height']}:{pixel_box['left']}:{pixel_box['top']}",
        '-f',
        'image2pipe',
        '-vcodec',
        'mjpeg',
        'pipe:1',
    ]
    runner = ffmpeg_runner or subprocess.run
    try:
        result = runner(command, input=image_bytes, capture_output=True, check=False)
    except (OSError, subprocess.SubprocessError, TypeError):
        return None

    stdout = getattr(result, 'stdout', b'') or b''
    returncode = int(getattr(result, 'returncode', 1))
    if returncode != 0 or not stdout:
        return None
    return 'data:image/jpeg;base64,' + base64.b64encode(stdout).decode('ascii')


def _decode_data_url(data_url: str) -> tuple[str, bytes] | None:
    if not data_url.startswith('data:') or ',' not in data_url:
        return None

    header, encoded = data_url.split(',', 1)
    if ';base64' not in header:
        return None

    mime_type = header[5:].split(';', 1)[0] or 'application/octet-stream'
    try:
        return mime_type, base64.b64decode(encoded)
    except (binascii.Error, ValueError):
        return None


def _mime_to_ffmpeg_codec(mime_type: str) -> str | None:
    return {
        'image/jpeg': 'mjpeg',
        'image/jpg': 'mjpeg',
        'image/png': 'png',
        'image/x-portable-pixmap': 'ppm',
    }.get(mime_type.lower())


def _crop_preview_with_cv2(image_bytes: bytes, pixel_box: dict[str, int]) -> str | None:
    if cv2 is None or np is None:
        return None

    try:
        decoded = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), getattr(cv2, 'IMREAD_COLOR', 1))
    except Exception:
        return None

    if decoded is None:
        return None

    top = pixel_box['top']
    left = pixel_box['left']
    bottom = top + pixel_box['height']
    right = left + pixel_box['width']
    cropped = decoded[top:bottom, left:right]

    try:
        ok, encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    except Exception:
        return None
    if not ok:
        return None
    return 'data:image/jpeg;base64,' + base64.b64encode(encoded.tobytes()).decode('ascii')


def _scale_value(value: Any, full_size: int) -> int:
    numeric = float(value or 0)
    if 0.0 <= numeric <= 1.0:
        return int(round(numeric * full_size))
    return int(round(numeric))


def _scale_extent(value: Any, full_size: int) -> int:
    numeric = float(value or 0)
    if 0.0 <= numeric <= 1.0:
        return int(round(numeric * full_size))
    return int(round(numeric))
