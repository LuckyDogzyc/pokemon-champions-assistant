from __future__ import annotations

from app.schemas.video import VideoSource
from app.services.video_source_service import VideoSourceService


FFMPEG_DSHOW_STDERR = """
[dshow @ 000001] DirectShow video devices (some may be both video and audio devices)
[dshow @ 000001]  "Integrated Camera"
[dshow @ 000001]     Alternative name "@device_pnp_\\?\\usb#vid_0bda&pid_58f4"
[dshow @ 000001]  "OBS Virtual Camera"
[dshow @ 000001]     Alternative name "@device_sw_foo"
[dshow @ 000001]  "USB Capture HDMI 4K+"
[dshow @ 000001]     Alternative name "@device_pnp_\\?\\usb#vid_534d&pid_2109"
[dshow @ 000001] DirectShow audio devices
[dshow @ 000001]  "Microphone"
""".strip()


class FakeCompletedProcess:
    def __init__(self, stderr: str) -> None:
        self.stderr = stderr
        self.stdout = ""
        self.returncode = 1


class StubVideoSourceService(VideoSourceService):
    def _detect_with_opencv(self) -> list[VideoSource]:
        return [
            VideoSource(
                id="0",
                label="Video Device 0",
                backend="opencv",
                is_capture_card_candidate=True,
                device_index=0,
            ),
            VideoSource(
                id="1",
                label="Video Device 1",
                backend="opencv",
                is_capture_card_candidate=False,
                device_index=1,
            ),
            VideoSource(
                id="2",
                label="Video Device 2",
                backend="opencv",
                is_capture_card_candidate=False,
                device_index=2,
            ),
        ]


def test_parse_dshow_video_device_names_ignores_alternative_names_and_audio_section() -> None:
    service = VideoSourceService(platform="win32")

    labels = service._parse_dshow_video_device_names(FFMPEG_DSHOW_STDERR)

    assert labels == ["Integrated Camera", "OBS Virtual Camera", "USB Capture HDMI 4K+"]


def test_list_sources_prefers_windows_friendly_names_when_ffmpeg_metadata_is_available() -> None:
    service = StubVideoSourceService(
        platform="win32",
        ffmpeg_runner=lambda command: FakeCompletedProcess(FFMPEG_DSHOW_STDERR),
    )

    sources = service.list_sources()

    assert [source.label for source in sources] == [
        "Integrated Camera",
        "OBS Virtual Camera",
        "USB Capture HDMI 4K+",
    ]
    assert sources[2].is_capture_card_candidate is True


class SparseIndexVideoSourceService(VideoSourceService):
    def _detect_with_opencv(self) -> list[VideoSource]:
        return [
            VideoSource(id="4", label="Video Device 4", backend="opencv", device_index=4),
            VideoSource(id="7", label="Video Device 7", backend="opencv", device_index=7),
        ]


def test_list_sources_maps_friendly_names_by_detected_order_when_device_indices_are_sparse() -> None:
    service = SparseIndexVideoSourceService(
        platform="win32",
        ffmpeg_runner=lambda command: FakeCompletedProcess(
            '\n'.join([
                '[dshow @ 000001] DirectShow video devices',
                '[dshow @ 000001]  "OBS Virtual Camera"',
                '[dshow @ 000001]  "USB Capture HDMI 4K+"',
                '[dshow @ 000001] DirectShow audio devices',
            ])
        ),
    )

    sources = service.list_sources()

    assert [source.label for source in sources] == ['OBS Virtual Camera', 'USB Capture HDMI 4K+']
    assert sources[1].is_capture_card_candidate is True


def test_resolve_ffmpeg_executable_falls_back_to_imageio_ffmpeg(monkeypatch) -> None:
    service = VideoSourceService(platform="win32")

    monkeypatch.setattr("app.services.video_source_service.shutil.which", lambda name: None)
    monkeypatch.setattr(
        "app.services.video_source_service.importlib.import_module",
        lambda name: type("StubImageIOFFmpeg", (), {"get_ffmpeg_exe": staticmethod(lambda: r"C:\bundle\ffmpeg.exe")})(),
    )

    assert service._resolve_ffmpeg_executable() == r"C:\bundle\ffmpeg.exe"


def test_decode_ffmpeg_output_prefers_utf8_before_windows_ansi() -> None:
    service = VideoSourceService(platform="win32")
    utf8_bytes = '"USB Capture HDMI ™"'.encode('utf-8')

    assert service._decode_ffmpeg_output(utf8_bytes) == '"USB Capture HDMI ™"'
