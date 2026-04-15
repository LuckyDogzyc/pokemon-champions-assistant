from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.phase import BattlePhase
from app.schemas.recognition import RecognitionSource


@dataclass
class RecognizedSideState:
    name: str | None = None
    confidence: float = 0.0
    source: RecognitionSource = RecognitionSource.MOCK


@dataclass
class RecognitionState:
    current_phase: BattlePhase = BattlePhase.UNKNOWN
    player: RecognizedSideState = field(default_factory=RecognizedSideState)
    opponent: RecognizedSideState = field(default_factory=RecognizedSideState)
    timestamp: str = ""
