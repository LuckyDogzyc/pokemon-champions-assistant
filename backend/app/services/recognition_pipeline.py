from __future__ import annotations

from app.schemas.phase import BattlePhase
from app.schemas.recognition import (
    RecognitionSource,
    RecognitionStatePayload,
    RecognizedSide,
    TeamPreviewState,
)
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
        layout_variant = frame.get("layout_variant") or frame.get("layout_variant_hint")

        if phase_result.phase == BattlePhase.TEAM_SELECT:
            annotation_target = frame.get("annotation_target", {})
            result = RecognitionStatePayload(
                current_phase=phase_result.phase,
                timestamp=frame.get("timestamp", ""),
                layout_variant=layout_variant,
                phase_evidence=list(phase_result.evidence),
                team_preview=TeamPreviewState(
                    player_team=list(annotation_target.get("player_team", [])),
                    opponent_team=list(annotation_target.get("opponent_team", [])),
                    selected_count=annotation_target.get("selected_count"),
                    instruction_text=annotation_target.get("instruction_text"),
                ),
            )
            self._last_result = result
            return result

        if phase_result.phase != BattlePhase.BATTLE:
            result = RecognitionStatePayload(
                current_phase=phase_result.phase,
                timestamp=frame.get("timestamp", ""),
                layout_variant=layout_variant,
                phase_evidence=list(phase_result.evidence),
            )
            self._last_result = result
            return result

        anchors = get_battle_name_anchors(frame)
        player = self._recognizer.recognize_side(frame, anchors["player"], "player")
        opponent = self._recognizer.recognize_side(frame, anchors["opponent"], "opponent")
        result = RecognitionStatePayload(
            current_phase=phase_result.phase,
            layout_variant=layout_variant,
            phase_evidence=list(phase_result.evidence),
            player=RecognizedSide(
                name=player.get("name"),
                confidence=player.get("confidence", 0.0),
                source=RecognitionSource(player.get("source", "mock")),
                debug_raw_text=player.get("raw_text"),
                debug_roi=player.get("roi"),
                matched_by=player.get("matched_by"),
            ),
            opponent=RecognizedSide(
                name=opponent.get("name"),
                confidence=opponent.get("confidence", 0.0),
                source=RecognitionSource(opponent.get("source", "mock")),
                debug_raw_text=opponent.get("raw_text"),
                debug_roi=opponent.get("roi"),
                matched_by=opponent.get("matched_by"),
            ),
            timestamp=frame.get("timestamp", ""),
        )
        self._last_result = result
        return result

    def get_current_state(self) -> RecognitionStatePayload:
        return self._last_result

    def override_side(self, side: str, name: str) -> RecognitionStatePayload:
        updated = self._last_result.model_copy(deep=True)
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
        self._last_result = updated
        return self._last_result
