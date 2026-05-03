from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class StubRecognitionPipeline:
    def __init__(self):
        from app.schemas.recognition import RecognitionSource, RecognitionStatePayload, RecognizedSide

        self.state = RecognitionStatePayload(
            current_phase="battle",
            player=RecognizedSide(name="喷火龙", confidence=0.9, source=RecognitionSource.MOCK),
            opponent=RecognizedSide(name="皮卡丘", confidence=0.8, source=RecognitionSource.MOCK),
            timestamp="2026-04-15T15:20:00Z",
        )

    def get_current_state(self):
        return self.state

    def override_side(self, side: str, name: str):
        from app.schemas.recognition import RecognitionSource, RecognizedSide

        updated = self.state.model_copy(deep=True)
        setattr(updated, side, RecognizedSide(name=name, confidence=1.0, source=RecognitionSource.MANUAL))
        self.state = updated
        return self.state


def test_manual_override_updates_player_side_to_manual_source(monkeypatch):
    from app.api import recognition as recognition_api
    from app.services.battle_session_store import BattleSessionStore

    monkeypatch.setattr(recognition_api, "recognition_pipeline", StubRecognitionPipeline())
    monkeypatch.setattr(recognition_api, "battle_session_store", BattleSessionStore())

    response = client.post(
        "/api/recognition/override",
        json={"side": "player", "name": "伊布"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["player"]["name"] == "伊布"
    assert payload["player"]["source"] == "manual"
    assert payload["player_active_name"] == "伊布"
    assert payload["battle_session"]["player_active"]["name"] == "伊布"
