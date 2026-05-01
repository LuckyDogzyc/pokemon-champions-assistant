from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BattlePhase(StrEnum):
    TEAM_SELECT = "team_select"
    SWITCHING = "switching"
    BATTLE = "battle"
    MOVE_RESOLUTION = "move_resolution"
    FINAL_RESULT = "final_result"
    UNKNOWN = "unknown"


class PhaseDetectionResult(BaseModel):
    phase: BattlePhase
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
