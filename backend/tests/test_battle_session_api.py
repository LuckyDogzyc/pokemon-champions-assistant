from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.phase import BattlePhase
from app.schemas.recognition import RecognitionSource, RecognitionStatePayload, RecognizedSide
from app.services.battle_session_store import BattleSessionStore


class StubRecognitionPipeline:
    def __init__(self) -> None:
        self._state = RecognitionStatePayload(
            current_phase=BattlePhase.BATTLE,
            player=RecognizedSide(name="喷火龙", confidence=0.9, source=RecognitionSource.OCR),
            opponent=RecognizedSide(name="皮卡丘", confidence=0.8, source=RecognitionSource.OCR),
            timestamp="test-ts",
        )

    def override_side(self, side: str, name: str) -> RecognitionStatePayload:
        updated = self._state.model_copy(deep=True)
        manual = RecognizedSide(name=name, confidence=1.0, source=RecognitionSource.MANUAL)
        if side == "player":
            updated.player = manual
        elif side == "opponent":
            updated.opponent = manual
        self._state = updated
        return updated


def test_battle_session_status_returns_current_session(monkeypatch) -> None:
    from app.api import recognition as recognition_api

    store = BattleSessionStore()
    store.sync_from_recognition(
        RecognitionStatePayload(
            current_phase=BattlePhase.BATTLE,
            player=RecognizedSide(name="喷火龙", confidence=0.9, source=RecognitionSource.OCR),
            opponent=RecognizedSide(name="皮卡丘", confidence=0.8, source=RecognitionSource.OCR),
            timestamp="test-ts",
        )
    )
    monkeypatch.setattr(recognition_api, "battle_session_store", store)

    client = TestClient(create_app())
    response = client.get("/api/battle-session/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_active"]["name"] == "喷火龙"
    assert payload["opponent_active"]["name"] == "皮卡丘"


def test_battle_session_manual_override_updates_session(monkeypatch) -> None:
    from app.api import recognition as recognition_api
    from app.services.battle_state_store import BattleStateStore

    monkeypatch.setattr(recognition_api, "recognition_pipeline", StubRecognitionPipeline())
    monkeypatch.setattr(recognition_api, "battle_state_store", BattleStateStore())
    monkeypatch.setattr(recognition_api, "battle_session_store", BattleSessionStore())

    client = TestClient(create_app())
    response = client.post(
        "/api/battle-session/manual-override",
        json={"side": "player", "name": "伊布"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_active"]["name"] == "伊布"
    assert payload["opponent_active"]["name"] == "皮卡丘"
    assert any(entry["text"] == "我方 派出了 伊布" for entry in payload["log"])
