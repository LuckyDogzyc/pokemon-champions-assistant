from __future__ import annotations

from app.schemas.phase import BattlePhase
from app.schemas.recognition import RecognitionSource, RecognitionStatePayload, RecognizedSide
from app.services.layout_anchors import get_battle_name_anchors
from app.services.phase_detector import PhaseDetector
from app.services.recognizers.mock_recognizer import MockSideRecognizer


class RecognitionPipeline:
    def __init__(self, phase_detector=None, recognizer=None) -> None:
        self._phase_detector = phase_detector or PhaseDetector()
        self._recognizer = recognizer or MockSideRecognizer()
        self._last_result = RecognitionStatePayload(timestamp="")

    def recognize(self, frame: dict) -> RecognitionStatePayload:
        phase_result = self._phase_detector.detect(frame)
        if phase_result.phase != BattlePhase.BATTLE:
            result = RecognitionStatePayload(
                current_phase=phase_result.phase,
                timestamp=frame.get("timestamp", ""),
            )
            self._last_result = result
            return result

        anchors = get_battle_name_anchors(frame)
        player = self._recognizer.recognize_side(frame, anchors["player"], "player")
        opponent = self._recognizer.recognize_side(frame, anchors["opponent"], "opponent")
        result = RecognitionStatePayload(
            current_phase=phase_result.phase,
            player=RecognizedSide(
                name=player.get("name"),
                confidence=player.get("confidence", 0.0),
                source=RecognitionSource(player.get("source", "mock")),
            ),
            opponent=RecognizedSide(
                name=opponent.get("name"),
                confidence=opponent.get("confidence", 0.0),
                source=RecognitionSource(opponent.get("source", "mock")),
            ),
            timestamp=frame.get("timestamp", ""),
        )
        self._last_result = result
        return result

    def get_current_state(self) -> RecognitionStatePayload:
        return self._last_result
