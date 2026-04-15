from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, computed_field

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


class RecognitionStatePayload(BaseModel):
    current_phase: BattlePhase = BattlePhase.UNKNOWN
    player: RecognizedSide = RecognizedSide()
    opponent: RecognizedSide = RecognizedSide()
    timestamp: str

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
