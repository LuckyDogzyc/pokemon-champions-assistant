from __future__ import annotations

from app.models.phase_state import PhaseState
from app.schemas.phase import BattlePhase, PhaseDetectionResult


class PhaseDetector:
    def detect(self, frame: dict) -> PhaseDetectionResult:
        ui = frame.get("ui", {}) if isinstance(frame, dict) else {}
        state = self._detect_state(ui)
        return PhaseDetectionResult(
            phase=state.phase,
            confidence=state.confidence,
            evidence=state.evidence,
        )

    def _detect_state(self, ui: dict) -> PhaseState:
        if ui.get("team_select_banner"):
            return PhaseState(
                phase=BattlePhase.TEAM_SELECT,
                confidence=0.95,
                evidence=["team_select_banner"],
            )
        if ui.get("switch_prompt"):
            return PhaseState(
                phase=BattlePhase.SWITCHING,
                confidence=0.9,
                evidence=["switch_prompt"],
            )
        if ui.get("move_resolution_text"):
            return PhaseState(
                phase=BattlePhase.MOVE_RESOLUTION,
                confidence=0.85,
                evidence=["move_resolution_text"],
            )
        if ui.get("battle_hud"):
            return PhaseState(
                phase=BattlePhase.BATTLE,
                confidence=0.9,
                evidence=["battle_hud"],
            )
        return PhaseState()
