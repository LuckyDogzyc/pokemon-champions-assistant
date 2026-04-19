from app.services.capture_session import CaptureSessionService, OpenCVCaptureReader, encode_preview_image
from app.services.frame_store import FrameStore


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeCaptureReader:
    def __init__(self) -> None:
        self.read_calls = 0

    def read(self, source_id: str):
        self.read_calls += 1
        return True, {
            "source_id": source_id,
            "frame_no": self.read_calls,
            "width": 1280,
            "height": 720,
            "preview_image_data_url": "data:image/jpeg;base64,base-preview",
        }


class FailingCaptureReader:
    def __init__(self) -> None:
        self.read_calls = 0

    def read(self, source_id: str):
        self.read_calls += 1
        return False, {"source_id": source_id, "error": "open_failed"}


def test_capture_session_uses_default_interval_and_updates_latest_frame():
    clock = FakeClock()
    reader = FakeCaptureReader()
    frame_store = FrameStore()
    session = CaptureSessionService(frame_store=frame_store, capture_reader=reader, now_fn=clock.now)

    state = session.start("device-0")

    assert state["running"] is True
    assert state["interval_seconds"] == 1
    assert state["latest_frame"]["source_id"] == "device-0"
    assert state["latest_frame"]["frame_variants"] == {
        "phase_frame": {
            "width": 640,
            "height": 360,
            "preview_image_data_url": "data:image/jpeg;base64,base-preview",
        },
        "roi_source_frame": {
            "width": 1280,
            "height": 720,
            "preview_image_data_url": "data:image/jpeg;base64,base-preview",
        },
    }
    assert reader.read_calls == 1

    clock.advance(0.5)
    polled = session.poll()
    assert polled["latest_frame"]["frame_no"] == 1
    assert reader.read_calls == 1

    clock.advance(0.5)
    polled = session.poll()
    assert polled["latest_frame"]["frame_no"] == 2
    assert reader.read_calls == 2


def test_capture_session_can_stop_and_report_not_running():
    clock = FakeClock()
    reader = FakeCaptureReader()
    session = CaptureSessionService(capture_reader=reader, now_fn=clock.now)

    session.start("device-1")
    stopped = session.stop()

    assert stopped["running"] is False
    assert stopped["source_id"] == "device-1"


def test_capture_session_returns_black_preview_when_active_source_capture_fails():
    clock = FakeClock()
    reader = FailingCaptureReader()
    session = CaptureSessionService(capture_reader=reader, now_fn=clock.now)

    state = session.start("device-9")

    assert state["running"] is True
    assert state["source_id"] == "device-9"
    assert state["latest_frame"]["source_id"] == "device-9"
    assert state["latest_frame"]["error"] == "open_failed"
    assert state["latest_frame"]["preview_image_data_url"].startswith("data:image/svg+xml;utf8,")
    assert state["latest_frame"]["frame_variants"] == {
        "phase_frame": {
            "width": None,
            "height": None,
            "preview_image_data_url": state["latest_frame"]["preview_image_data_url"],
        },
        "roi_source_frame": {
            "width": None,
            "height": None,
            "preview_image_data_url": state["latest_frame"]["preview_image_data_url"],
        },
    }
    assert reader.read_calls == 1


class FakeFfmpegCompletedProcess:
    def __init__(self, stdout: bytes = b'', stderr: bytes = b'', returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_opencv_capture_reader_routes_virtual_source_through_opencv_backend(monkeypatch):
    """Virtual devices (OBS Virtual Camera, vcam) use opencv backend for stable persistent capture."""
    from app.services import capture_session as capture_session_module

    class FakeEncoded:
        def __init__(self, data):
            self._data = data

        def tobytes(self):
            return self._data

    class StubFrame:
        def __init__(self, shape, marker):
            self.shape = shape
            self.marker = marker

    class StubCv2:
        IMWRITE_JPEG_QUALITY = 1
        IMWRITE_WEBP_QUALITY = 32

        @staticmethod
        def VideoCapture(capture_target, apiPreference=None):
            return StubOpenCvCapture(opened=True)

        @staticmethod
        def resize(image, dsize, fx=None, fy=None, interpolation=None):
            marker = 'phase' if dsize[0] <= 320 else 'base_resized'
            return StubFrame((dsize[1], dsize[0], 3), marker=marker)

        @staticmethod
        def imencode(ext, img, params=None):
            marker = getattr(img, 'marker', None)
            if marker == 'phase':
                return (True, FakeEncoded(b'phase-jpeg'))
            if marker == 'base_resized':
                return (True, FakeEncoded(b'base-jpeg'))
            return (True, FakeEncoded(b'raw-base-jpeg'))

    class StubOpenCvCapture:
        def __init__(self, opened: bool):
            self._opened = opened

        def isOpened(self):
            return self._opened

        def read(self):
            return True, StubFrame((720, 1280, 3), marker='base')

        def release(self):
            pass

    reader = OpenCVCaptureReader(
        ffmpeg_resolver=lambda: r'C:\\bundle\\ffmpeg.exe',
        ffmpeg_runner=lambda command: FakeFfmpegCompletedProcess(stdout=b'ffmpeg-should-not-run'),
    )

    monkeypatch.setattr(capture_session_module, 'cv2', StubCv2)

    ok, payload = reader.read(
        {
            'id': '1',
            'label': 'OBS Virtual Camera',
            'backend': 'opencv',
            'capture_selector': 'OBS Virtual Camera',
            'device_kind': 'virtual',
        }
    )

    assert ok is True
    assert payload['source_id'] == '1'
    assert payload['capture_method'] == 'opencv'
    assert payload['capture_backend'] == 'opencv'
    assert payload['preview_image_data_url'] == 'data:image/jpeg;base64,YmFzZS1qcGVn'
    assert payload['frame_variants'] == {
        'phase_frame': {
            'width': 320,
            'height': 180,
            'preview_image_data_url': 'data:image/jpeg;base64,cGhhc2UtanBlZw==',
        },
        'roi_source_frame': {
            'width': 1280,
            'height': 720,
            'preview_image_data_url': 'data:image/jpeg;base64,YmFzZS1qcGVn',
        },
    }


def test_dshow_source_does_not_fall_back_to_opencv_index_when_ffmpeg_capture_fails(monkeypatch):
    from app.services import capture_session as capture_session_module

    class StubCv2:
        @staticmethod
        def VideoCapture(*args, **kwargs):  # pragma: no cover - should never be hit in this test
            raise AssertionError('dshow source should not fall back to OpenCV index capture when ffmpeg fails')

    reader = OpenCVCaptureReader(
        ffmpeg_resolver=lambda: r'C:\\bundle\\ffmpeg.exe',
        ffmpeg_runner=lambda command: FakeFfmpegCompletedProcess(stderr=b'device returned no frames', returncode=1),
    )

    monkeypatch.setattr(capture_session_module, 'cv2', StubCv2)

    ok, payload = reader.read(
        {
            'id': '1',
            'label': 'USB Capture HDMI 4K+',
            'backend': 'dshow',
            'capture_selector': 'USB Capture HDMI 4K+',
            'device_kind': 'physical',
            'device_index': 1,
        }
    )

    assert ok is False
    assert payload['source_id'] == '1'
    assert payload['error'] == 'ffmpeg_read_failed'
    assert payload['error_detail'] == 'device returned no frames'
    assert payload['capture_method'] == 'ffmpeg-dshow'
    assert payload['capture_backend'] == 'dshow'


def test_dshow_source_retries_with_probed_video_size_and_framerate_after_default_failure(monkeypatch):
    from app.services import capture_session as capture_session_module

    commands: list[list[str]] = []

    def ffmpeg_runner(command: list[str]):
        commands.append(command)
        joined = ' '.join(command)
        if '-list_options true' in joined:
            return FakeFfmpegCompletedProcess(
                stderr=(
                    b'[dshow @ 000001]   pin "Capture"\n'
                    b'[dshow @ 000001]   vcodec=mjpeg  min s=1920x1080 fps=30 max s=1920x1080 fps=30\n'
                ),
                returncode=1,
            )
        if '-video_size 1920x1080' in joined and '-framerate 30' in joined:
            return FakeFfmpegCompletedProcess(stdout=b'jpeg-bytes', returncode=0)
        return FakeFfmpegCompletedProcess(stderr=b'device returned no frames', returncode=1)

    class StubCv2:
        @staticmethod
        def VideoCapture(*args, **kwargs):  # pragma: no cover - should never be hit in this test
            raise AssertionError('dshow source should not fall back to OpenCV index capture when ffmpeg retries are available')

    reader = OpenCVCaptureReader(
        ffmpeg_resolver=lambda: r'C:\\bundle\\ffmpeg.exe',
        ffmpeg_runner=ffmpeg_runner,
    )

    monkeypatch.setattr(capture_session_module, 'cv2', StubCv2)

    ok, payload = reader.read(
        {
            'id': '2',
            'label': 'USB Capture HDMI 4K+',
            'backend': 'dshow',
            'capture_selector': 'USB Capture HDMI 4K+',
            'device_kind': 'physical',
        }
    )

    assert ok is True
    assert payload['capture_method'] == 'ffmpeg-dshow'
    assert payload['capture_backend'] == 'dshow'
    assert payload['preview_image_data_url'] == 'data:image/jpeg;base64,anBlZy1ieXRlcw=='
    assert any('-list_options' in ' '.join(command) for command in commands)
    assert any('-video_size 1920x1080' in ' '.join(command) and '-framerate 30' in ' '.join(command) for command in commands)


def test_encode_preview_image_returns_jpeg_data_url(monkeypatch):
    from app.services import capture_session as capture_session_module

    class StubEncodedFrame:
        def tobytes(self):
            return b'jpeg-bytes'

    class StubCv2:
        IMWRITE_JPEG_QUALITY = 1

        @staticmethod
        def imencode(ext, frame, params):
            assert ext == '.jpg'
            return True, StubEncodedFrame()

    monkeypatch.setattr(capture_session_module, 'cv2', StubCv2)

    class FakeFrame:
        shape = (480, 320, 3)

    result = encode_preview_image(FakeFrame())

    assert result == 'data:image/jpeg;base64,anBlZy1ieXRlcw=='
