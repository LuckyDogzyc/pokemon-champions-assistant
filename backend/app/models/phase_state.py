from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.phase import BattlePhase


@dataclass
class PhaseState:
    phase: BattlePhase = BattlePhase.UNKNOWN
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
