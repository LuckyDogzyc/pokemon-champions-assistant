from app.schemas.phase import BattlePhase
from app.schemas.recognition import RecognizedSide, RecognitionSource, RecognitionStatePayload


def test_recognition_state_serializes_phase_names_confidence_and_source():
    payload = RecognitionStatePayload(
        current_phase=BattlePhase.BATTLE,
        player=RecognizedSide(name="喷火龙", confidence=0.98, source=RecognitionSource.OCR),
        opponent=RecognizedSide(name="皮卡丘", confidence=0.88, source=RecognitionSource.MANUAL),
        timestamp="2026-04-15T14:30:00Z",
    )

    data = payload.model_dump(mode="json")

    assert data["current_phase"] == "battle"
    assert data["player"]["name"] == "喷火龙"
    assert data["player"]["confidence"] == 0.98
    assert data["player"]["source"] == "ocr"
    assert data["opponent"]["source"] == "manual"
    assert data["timestamp"] == "2026-04-15T14:30:00Z"


def test_recognition_state_model_exposes_flattened_active_names():
    payload = RecognitionStatePayload(
        current_phase=BattlePhase.SWITCHING,
        player=RecognizedSide(name="伊布", confidence=0.6, source=RecognitionSource.MOCK),
        opponent=RecognizedSide(name="妙蛙种子", confidence=0.7, source=RecognitionSource.OCR),
        timestamp="2026-04-15T14:31:00Z",
    )

    assert payload.player_active_name == "伊布"
    assert payload.opponent_active_name == "妙蛙种子"
