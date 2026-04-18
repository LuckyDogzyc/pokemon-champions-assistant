from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
                "error_detail": "device returned no frames",
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
                "error_detail": "device returned no frames",
            },
        }


class StubRecognitionPipeline:
    def recognize(self, frame):
        from app.schemas.recognition import RecognitionSource, RecognitionStatePayload, RecognizedSide

        return RecognitionStatePayload(
            current_phase="battle",
            player=RecognizedSide(name="喷火龙", confidence=0.98, source=RecognitionSource.MOCK),
            opponent=RecognizedSide(name="皮卡丘", confidence=0.87, source=RecognitionSource.MOCK),
            timestamp=frame["timestamp"],
        )

    def get_current_state(self):
        return self.recognize({"timestamp": "2026-04-15T15:10:00Z"})


def test_start_recognition_session_returns_running_state(monkeypatch):
    from app.api import recognition as recognition_api

    monkeypatch.setattr(recognition_api, "capture_session_service", StubCaptureSessionService())
    monkeypatch.setattr(recognition_api, "recognition_pipeline", StubRecognitionPipeline())

    response = client.post("/api/recognition/session/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["running"] is True
    assert payload["current_state"]["current_phase"] == "battle"
    assert payload["current_state"]["player_active_name"] == "喷火龙"
    assert payload["current_state"]["preview_image_data_url"] == "data:image/jpeg;base64,stub-preview"
    assert payload["current_state"]["capture_error"] == "ffmpeg_read_failed"
    assert payload["current_state"]["capture_error_detail"] == "device returned no frames"
    assert payload["current_state"]["capture_method"] == "ffmpeg-dshow"
    assert payload["current_state"]["capture_backend"] == "dshow"


def test_get_current_recognition_returns_phase_names_confidence_and_source(monkeypatch):
    from app.api import recognition as recognition_api

    monkeypatch.setattr(recognition_api, "capture_session_service", StubCaptureSessionService())
    monkeypatch.setattr(recognition_api, "recognition_pipeline", StubRecognitionPipeline())

    response = client.get("/api/recognition/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_phase"] == "battle"
    assert payload["player_active_name"] == "喷火龙"
    assert payload["opponent_active_name"] == "皮卡丘"
    assert payload["player"]["confidence"] == 0.98
    assert payload["opponent"]["confidence"] == 0.87
    assert payload["input_source"] == "device-0"
    assert payload["preview_image_data_url"] == "data:image/jpeg;base64,stub-preview"
    assert payload["capture_error"] == "ffmpeg_read_failed"
    assert payload["capture_error_detail"] == "device returned no frames"
    assert payload["capture_method"] == "ffmpeg-dshow"
    assert payload["capture_backend"] == "dshow"
