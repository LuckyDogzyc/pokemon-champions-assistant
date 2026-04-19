from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, computed_field

from app.schemas.phase import BattlePhase


class RecognitionSource(StrEnum):
    OCR = "ocr"
    MANUAL = "manual"
    MOCK = "mock"


class OverrideSide(StrEnum):
    PLAYER = "player"
    OPPONENT = "opponent"


class RecognizedSide(BaseModel):
    name: str | None = None
    confidence: float = 0.0
    source: RecognitionSource = RecognitionSource.MOCK
    debug_raw_text: str | None = None
    debug_roi: dict[str, float | str] | None = None
    matched_by: str | None = None


class TeamPreviewState(BaseModel):
    player_team: list[str] = Field(default_factory=list)
    opponent_team: list[str] = Field(default_factory=list)
    selected_count: int | None = None
    instruction_text: str | None = None


class RecognitionStatePayload(BaseModel):
    current_phase: BattlePhase = BattlePhase.UNKNOWN
    player: RecognizedSide = Field(default_factory=RecognizedSide)
    opponent: RecognizedSide = Field(default_factory=RecognizedSide)
    timestamp: str
    layout_variant: str | None = None
    phase_evidence: list[str] = Field(default_factory=list)
    phase_snapshot: dict[str, str | float | list[str]] | None = None
    roi_payloads: dict[str, dict[str, Any]] = Field(default_factory=dict)
    team_preview: TeamPreviewState | None = None
    preview_image_data_url: str | None = None

    @computed_field
    @property
    def player_active_name(self) -> str | None:
        return self.player.name

    @computed_field
    @property
    def opponent_active_name(self) -> str | None:
        return self.opponent.name


class ManualOverrideRequest(BaseModel):
    side: OverrideSide
    name: str
