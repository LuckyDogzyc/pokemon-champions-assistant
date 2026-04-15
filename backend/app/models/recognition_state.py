from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.phase import BattlePhase
from app.schemas.recognition import RecognitionSource


@dataclass
class RecognizedSideState:
    name: str | None = None
    confidence: float = 0.0
    source: RecognitionSource = RecognitionSource.MOCK
    debug_raw_text: str | None = None
    debug_roi: dict[str, float | str] | None = None
    matched_by: str | None = None


@dataclass
class TeamPreviewModel:
    player_team: list[str] = field(default_factory=list)
    opponent_team: list[str] = field(default_factory=list)
    selected_count: int | None = None
    instruction_text: str | None = None


@dataclass
class RecognitionState:
    current_phase: BattlePhase = BattlePhase.UNKNOWN
    player: RecognizedSideState = field(default_factory=RecognizedSideState)
    opponent: RecognizedSideState = field(default_factory=RecognizedSideState)
    timestamp: str = ""
    layout_variant: str | None = None
    phase_evidence: list[str] = field(default_factory=list)
    team_preview: TeamPreviewModel | None = None
