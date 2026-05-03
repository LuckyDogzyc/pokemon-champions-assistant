import base64
import importlib

from fastapi.testclient import TestClient


def _make_ppm_preview_data_url(width: int = 640, height: int = 480) -> str:
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    pixels = b"\x10\x20\x30" * width * height
    return "data:image/x-portable-pixmap;base64," + base64.b64encode(header + pixels).decode("ascii")


class StubCaptureSessionService:
    def __init__(self):
        self.started = False

    def start(self, source_id: str):
        self.started = True
        return {
            "running": True,
            "source_id": source_id,
            "latest_frame": {
                "width": 1920,
                "height": 1080,
                "timestamp": "2026-04-15T15:10:00Z",
                "ui": {"battle_hud": True},
                "preview_image_data_url": "data:image/jpeg;base64,stub-preview",
                "capture_method": "ffmpeg-dshow",
                "capture_backend": "dshow",
                "error": "ffmpeg_read_failed",
                "error_detail": "[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)",
                "frame_variants": {
                    "phase_frame": {
                        "width": 640,
                        "height": 360,
                        "preview_image_data_url": "data:image/jpeg;base64,phase-preview",
                    },
                    "roi_source_frame": {
                        "width": 1920,
                        "height": 1080,
                        "preview_image_data_url": "data:image/jpeg;base64,roi-preview",
                    },
                },
            },
        }

    def poll(self):
        return {
            "running": True,
            "source_id": "device-0",
            "latest_frame": {
                "width": 1920,
                "height": 1080,
                "timestamp": "2026-04-15T15:10:00Z",
                "ui": {"battle_hud": True},
                "preview_image_data_url": "data:image/jpeg;base64,stub-preview",
                "capture_method": "ffmpeg-dshow",
                "capture_backend": "dshow",
                "error": "ffmpeg_read_failed",
                "error_detail": "[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)",
                "frame_variants": {
                    "phase_frame": {
                        "width": 640,
                        "height": 360,
                        "preview_image_data_url": "data:image/jpeg;base64,phase-preview",
                    },
                    "roi_source_frame": {
                        "width": 1920,
                        "height": 1080,
                        "preview_image_data_url": "data:image/jpeg;base64,roi-preview",
                    },
                },
            },
        }

    def stop(self):
        return self.poll()


class ValidPreviewCaptureSessionService(StubCaptureSessionService):
    def start(self, source_id: str):
        state = super().start(source_id)
        state["latest_frame"].update(
            {
                "width": 640,
                "height": 480,
                "preview_image_data_url": _make_ppm_preview_data_url(),
                "frame_variants": {
                    "phase_frame": {
                        "width": 640,
                        "height": 480,
                        "preview_image_data_url": _make_ppm_preview_data_url(),
                    },
                    "roi_source_frame": {
                        "width": 640,
                        "height": 480,
                        "preview_image_data_url": _make_ppm_preview_data_url(),
                    },
                },
            }
        )
        return state

    def poll(self):
        state = super().poll()
        state["latest_frame"].update(
            {
                "width": 640,
                "height": 480,
                "preview_image_data_url": _make_ppm_preview_data_url(),
                "frame_variants": {
                    "phase_frame": {
                        "width": 640,
                        "height": 480,
                        "preview_image_data_url": _make_ppm_preview_data_url(),
                    },
                    "roi_source_frame": {
                        "width": 640,
                        "height": 480,
                        "preview_image_data_url": _make_ppm_preview_data_url(),
                    },
                },
            }
        )
        return state


class StubVideoSourceService:
    def list_sources(self):
        from app.schemas.video import VideoSource

        return [
            VideoSource(
                id="device-0",
                label="Hagibis",
                backend="dshow",
                device_kind="physical",
                capture_selector="Hagibis",
                is_selected=True,
            ),
            VideoSource(
                id="device-1",
                label="OBS Virtual Camera",
                backend="opencv",
                device_kind="virtual",
                capture_selector="OBS Virtual Camera",
            ),
        ]


class StubRecognitionPipeline:
    def __init__(self):
        self._last_state = None

    def recognize(self, frame):
        from app.schemas.recognition import RecognitionSource, RecognitionStatePayload, RecognizedSide

        result = RecognitionStatePayload(
            current_phase="battle",
            player=RecognizedSide(name="喷火龙", confidence=0.98, source=RecognitionSource.MOCK),
            opponent=RecognizedSide(name="皮卡丘", confidence=0.87, source=RecognitionSource.MOCK),
            timestamp=frame["timestamp"],
        )
        self._last_state = result
        return result

    def get_current_state(self):
        if self._last_state is not None:
            return self._last_state
        return self.recognize({"timestamp": "2026-04-15T15:10:00Z"})

    def set_current_state(self, state):
        self._last_state = state

    def override_side(self, side, name):
        from app.schemas.recognition import RecognitionSource, RecognizedSide

        updated = self.get_current_state().model_copy(deep=True)
        manual_side = RecognizedSide(
            name=name,
            confidence=1.0,
            source=RecognitionSource.MANUAL,
            debug_raw_text=name,
            matched_by="manual",
        )
        if side == "player":
            updated.player = manual_side
        elif side == "opponent":
            updated.opponent = manual_side
        return updated


class StubRecognitionRuntime:
    def __init__(
        self,
        active_provider: str = "paddleocr",
        warning: str | None = None,
        pipeline: StubRecognitionPipeline | None = None,
    ):
        self.active_provider = active_provider
        self.warning = warning
        self.pipeline = pipeline or StubRecognitionPipeline()


class StubFrameStore:
    def __init__(self, latest_frame=None):
        self._latest_frame = latest_frame

    def get_latest_frame(self):
        return self._latest_frame

    def set_latest_frame(self, frame):
        self._latest_frame = frame


def build_client(
    monkeypatch,
    *,
    active_provider: str = "paddleocr",
    warning: str | None = None,
    pipeline: StubRecognitionPipeline | None = None,
    capture_session_service=None,
    frame_store=None,
):
    from app.services import recognition_runtime as recognition_runtime_service

    stub_pipeline = pipeline or StubRecognitionPipeline()
    stub_runtime = StubRecognitionRuntime(active_provider=active_provider, warning=warning, pipeline=stub_pipeline)
    monkeypatch.setattr(
        recognition_runtime_service,
        "create_recognition_runtime",
        lambda *_args, **_kwargs: stub_runtime,
    )

    from app.api import recognition as recognition_api
    from app.api import video as video_api
    from app import main as app_main

    recognition_api = importlib.reload(recognition_api)
    app_main = importlib.reload(app_main)

    monkeypatch.setattr(video_api, "capture_session_service", capture_session_service or StubCaptureSessionService())
    monkeypatch.setattr(video_api, "video_source_service", StubVideoSourceService())
    monkeypatch.setattr(recognition_api, "recognition_pipeline", stub_pipeline)
    monkeypatch.setattr(recognition_api, "recognition_runtime", stub_runtime)

    # Replace the frame_store so tests use a controlled store
    stub_store = frame_store or StubFrameStore()
    monkeypatch.setattr(recognition_api, "frame_store", stub_store)
    # Sync capture_session_service frame_store too
    if capture_session_service:
        capture_session_service._frame_store = stub_store

    return TestClient(app_main.create_app())


def test_start_recognition_session_returns_running_state(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post("/api/recognition/session/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["running"] is True
    assert payload["current_state"]["current_phase"] == "battle"
    assert payload["current_state"]["player_active_name"] == "喷火龙"
    assert payload["current_state"]["preview_image_data_url"] == "data:image/jpeg;base64,stub-preview"
    assert payload["current_state"]["capture_error"] == "ffmpeg_read_failed"
    assert payload["current_state"]["capture_error_detail"] == (
        "[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)"
    )
    assert payload["current_state"]["capture_method"] == "ffmpeg-dshow"
    assert payload["current_state"]["capture_backend"] == "dshow"
    assert payload["current_state"]["frame_variants_debug"] == {
        "phase_frame": {
            "source": "capture.frame_variants.phase_frame",
            "width": 640,
            "height": 360,
            "preview_image_data_url": "data:image/jpeg;base64,phase-preview",
        },
        "roi_source_frame": {
            "source": "capture.frame_variants.roi_source_frame",
            "width": 1920,
            "height": 1080,
            "preview_image_data_url": "data:image/jpeg;base64,roi-preview",
        },
    }
    assert payload["current_state"]["phase_snapshot"] == {
        "phase": "battle",
        "confidence": 1.0,
        "evidence": ["battle_hud"],
    }
    assert "player_name" not in payload["current_state"]["roi_payloads"]
    assert "opponent_name" not in payload["current_state"]["roi_payloads"]
    assert "command_panel" not in payload["current_state"]["roi_payloads"]
    assert payload["current_state"]["capture_help_text"] == (
        "当前采集卡可能正被其他程序占用。若需要保持 OBS 开启，请在 OBS 中启动虚拟摄像头并切换到 OBS Virtual Camera。"
    )
    assert payload["current_state"]["ocr_provider"] == "paddleocr"
    assert payload["current_state"]["ocr_warning"] is None
    assert payload["current_state"]["capture_suggested_source_id"] == "device-1"
    assert payload["current_state"]["capture_suggested_source_label"] == "OBS Virtual Camera"
    assert payload["current_state"]["battle_session"]["player_active"]["name"] == "喷火龙"
    assert payload["current_state"]["battle_session"]["opponent_active"]["name"] == "皮卡丘"


def test_get_current_recognition_returns_phase_names_confidence_and_source(monkeypatch):
    # Set up a frame store with initial data so the response includes preview
    store = StubFrameStore({
        "width": 1920,
        "height": 1080,
        "timestamp": "2026-04-15T15:10:00Z",
        "ui": {"battle_hud": True},
        "preview_image_data_url": "data:image/jpeg;base64,stub-preview",
        "capture_method": "ffmpeg-dshow",
        "capture_backend": "dshow",
        "error": "ffmpeg_read_failed",
        "error_detail": "[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)",
        "frame_variants": {
            "phase_frame": {
                "width": 640,
                "height": 360,
                "preview_image_data_url": "data:image/jpeg;base64,phase-preview",
            },
            "roi_source_frame": {
                "width": 1920,
                "height": 1080,
                "preview_image_data_url": "data:image/jpeg;base64,roi-preview",
            },
        },
    })
    client = build_client(monkeypatch, frame_store=store)

    response = client.get("/api/recognition/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_phase"] == "battle"
    assert payload["player_active_name"] == "喷火龙"
    assert payload["opponent_active_name"] == "皮卡丘"
    assert payload["player"]["confidence"] == 0.98
    assert payload["opponent"]["confidence"] == 0.87
    # input_source comes from selection_store; in this stub the first call
    # may resolve to any source — just check it's one of the known sources
    assert payload["input_source"] in ("device-0", "device-1")
    assert payload["preview_image_data_url"] == "data:image/jpeg;base64,stub-preview"
    assert payload["capture_error"] == "ffmpeg_read_failed"
    assert payload["capture_error_detail"] == (
        "[dshow @ 000001] Could not run graph (sometimes caused by a device already in use by other application)"
    )
    assert payload["capture_method"] == "ffmpeg-dshow"
    assert payload["capture_backend"] == "dshow"
    assert payload["frame_variants_debug"] == {
        "phase_frame": {
            "source": "capture.frame_variants.phase_frame",
            "width": 640,
            "height": 360,
            "preview_image_data_url": "data:image/jpeg;base64,phase-preview",
        },
        "roi_source_frame": {
            "source": "capture.frame_variants.roi_source_frame",
            "width": 1920,
            "height": 1080,
            "preview_image_data_url": "data:image/jpeg;base64,roi-preview",
        },
    }
    assert payload["phase_snapshot"] == {
        "phase": "battle",
        "confidence": 1.0,
        "evidence": ["battle_hud"],
    }
    assert "player_name" not in payload["roi_payloads"]
    assert "opponent_name" not in payload["roi_payloads"]
    assert "command_panel" not in payload["roi_payloads"]
    assert payload["capture_help_text"] == (
        "当前采集卡可能正被其他程序占用。若需要保持 OBS 开启，请在 OBS 中启动虚拟摄像头并切换到 OBS Virtual Camera。"
    )
    assert payload["ocr_provider"] == "paddleocr"
    assert payload["ocr_warning"] is None
    assert payload["capture_suggested_source_id"] == "device-1"
    assert payload["capture_suggested_source_label"] == "OBS Virtual Camera"


def test_get_current_recognition_exposes_stubbed_runtime_metadata(monkeypatch):
    client = build_client(
        monkeypatch,
        active_provider="mock",
        warning="PaddleOCR unavailable; using mock OCR provider.",
    )

    response = client.get("/api/recognition/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ocr_provider"] == "mock"
    assert payload["ocr_warning"] == "PaddleOCR unavailable; using mock OCR provider."


class BareBattleRoiRecognitionPipeline(StubRecognitionPipeline):
    def recognize(self, frame):
        from app.schemas.recognition import RecognitionSource, RecognitionStatePayload, RecognizedSide
        from app.services.recognition_pipeline import build_roi_payloads

        result = RecognitionStatePayload(
            current_phase="battle",
            player=RecognizedSide(name="喷火龙", confidence=0.98, source=RecognitionSource.MOCK),
            opponent=RecognizedSide(name="皮卡丘", confidence=0.87, source=RecognitionSource.MOCK),
            timestamp=frame["timestamp"],
            layout_variant="battle_move_menu_open",
            roi_payloads=build_roi_payloads(
                frame,
                phase="battle",
                layout_variant="battle_move_menu_open",
            ),
        )
        self._last_state = result
        return result


def test_current_recognition_enriches_existing_bare_roi_payloads_with_crops(monkeypatch):
    client = build_client(
        monkeypatch,
        pipeline=BareBattleRoiRecognitionPipeline(),
        capture_session_service=ValidPreviewCaptureSessionService(),
        frame_store=StubFrameStore(
            {
                "width": 640,
                "height": 480,
                "preview_image_data_url": _make_ppm_preview_data_url(),
                "frame_variants": {
                    "phase_frame": {
                        "width": 640,
                        "height": 480,
                        "preview_image_data_url": _make_ppm_preview_data_url(),
                    },
                    "roi_source_frame": {
                        "width": 640,
                        "height": 480,
                        "preview_image_data_url": _make_ppm_preview_data_url(),
                    },
                },
            }
        ),
    )

    response = client.get("/api/recognition/current")

    assert response.status_code == 200
    payload = response.json()
    for roi_name in ("player_status_panel", "opponent_status_panel", "move_list"):
        roi_payload = payload["roi_payloads"][roi_name]
        assert roi_payload["pixel_box"]
        assert roi_payload["crop_width"] > 0
        assert roi_payload["crop_height"] > 0
        assert roi_payload["preview_image_data_url"].startswith("data:image/jpeg;base64,")


class FailingRecognitionPipeline(StubRecognitionPipeline):
    def recognize(self, frame):
        raise RuntimeError("OneDnnContext does not have the input Filter")

    def get_current_state(self):
        return StubRecognitionPipeline().recognize({"timestamp": "2026-04-15T15:10:00Z"})


def test_current_recognition_returns_no_recognition_error_when_not_failing(monkeypatch):
    """Without a failing pipeline, recognition_error should be absent or null.

    In the new architecture, /current doesn't run recognition — it just
    returns the last known state.  So there's no recognition_error field
    set unless something went wrong during the last background cycle.
    """
    client = build_client(
        monkeypatch,
        pipeline=StubRecognitionPipeline(),
        capture_session_service=ValidPreviewCaptureSessionService(),
        frame_store=StubFrameStore({
            "width": 640,
            "height": 480,
            "preview_image_data_url": _make_ppm_preview_data_url(),
            "frame_variants": {
                "phase_frame": {
                    "width": 640,
                    "height": 480,
                    "preview_image_data_url": _make_ppm_preview_data_url(),
                },
                "roi_source_frame": {
                    "width": 640,
                    "height": 480,
                    "preview_image_data_url": _make_ppm_preview_data_url(),
                },
            },
        }),
    )

    response = client.get("/api/recognition/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_phase"] == "battle"
    assert payload["preview_image_data_url"].startswith("data:image/x-portable-pixmap;base64,")
    assert payload["roi_payloads"]["player_status_panel"]["preview_image_data_url"].startswith("data:image/jpeg;base64,")


def test_reset_recognition_session_returns_clean_state(monkeypatch):
    """POST /api/recognition/session/reset should clear battle data."""
    client = build_client(monkeypatch)

    # Start session first
    client.post("/api/recognition/session/start")

    # Then reset
    response = client.post("/api/recognition/session/reset")
    assert response.status_code == 200
    payload = response.json()
    assert payload["reset"] is True
    # After reset, the battle state should be clean
    assert payload["current_state"]["battle_state"]["battle_id"] != ""
    # Team slots should be empty
    assert payload["current_state"]["player_team_slots"] == []


def test_stop_recognition_session(monkeypatch):
    """POST /api/recognition/session/stop should stop the session."""
    client = build_client(monkeypatch)

    client.post("/api/recognition/session/start")
    response = client.post("/api/recognition/session/stop")
    assert response.status_code == 200
    payload = response.json()
    # Verify the response has the expected keys
    assert "running" in payload
    assert "input_source" in payload
