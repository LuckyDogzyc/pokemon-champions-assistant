from app.services.capture_session import CaptureSessionService, encode_preview_image
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
        return True, {"source_id": source_id, "frame_no": self.read_calls}


def test_capture_session_uses_default_interval_and_updates_latest_frame():
    clock = FakeClock()
    reader = FakeCaptureReader()
    frame_store = FrameStore()
    session = CaptureSessionService(frame_store=frame_store, capture_reader=reader, now_fn=clock.now)

    state = session.start("device-0")

    assert state["running"] is True
    assert state["interval_seconds"] == 3
    assert state["latest_frame"]["source_id"] == "device-0"
    assert reader.read_calls == 1

    clock.advance(2)
    polled = session.poll()
    assert polled["latest_frame"]["frame_no"] == 1
    assert reader.read_calls == 1

    clock.advance(1)
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
