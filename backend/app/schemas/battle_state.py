from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StatStageRange(int):
    """Ability stage change: -6 to +6."""
    ...


class FieldCondition(StrEnum):
    NONE = "none"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    SNOW = "snow"
    TRICK_ROOM = "trick_room"
    TAILWIND_PLAYER = "tailwind_player"
    TAILWIND_OPPONENT = "tailwind_opponent"
    REFLECT_PLAYER = "reflect_player"
    REFLECT_OPPONENT = "reflect_opponent"
    LIGHT_SCREEN_PLAYER = "light_screen_player"
    LIGHT_SCREEN_OPPONENT = "light_screen_opponent"
    AURORA_VEIL_PLAYER = "aurora_veil_player"
    AURORA_VEIL_OPPONENT = "aurora_veil_opponent"


class StatusCondition(StrEnum):
    NONE = "none"
    BURN = "burn"
    POISON = "poison"
    BAD_POISON = "bad_poison"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    CONFUSION = "confusion"
    FLINCH = "flinch"


class StatStages(BaseModel):
    """Battle stat stages for a single mon (-6 to +6)."""
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0


class MonBattleState(BaseModel):
    """Tracked state for a single Pokémon on the field."""
    pokemon_id: str | None = None
    name: str | None = None
    level: int = 50
    current_hp_percent: float | None = None
    status: StatusCondition = StatusCondition.NONE
    stat_stages: StatStages = Field(default_factory=StatStages)
    revealed_moves: list[str] = Field(default_factory=list)
    item_revealed: str | None = None
    ability_revealed: str | None = None
    turns_on_field: int = 0


class TeamEntry(BaseModel):
    """A Pokémon in the team roster (not necessarily on the field)."""
    pokemon_id: str | None = None
    name: str | None = None
    is_active: bool = False
    is_fainted: bool = False


class BattleState(BaseModel):
    """Full snapshot of tracked battle state."""
    battle_id: str = ""
    turn: int = 0
    phase: str = "unknown"
    field_conditions: list[FieldCondition] = Field(default_factory=list)
    player_active: MonBattleState = Field(default_factory=MonBattleState)
    opponent_active: MonBattleState = Field(default_factory=MonBattleState)
    player_team: list[TeamEntry] = Field(default_factory=list)
    opponent_team: list[TeamEntry] = Field(default_factory=list)
    move_log: list[dict[str, Any]] = Field(default_factory=list)
    hp_history: list[dict[str, Any]] = Field(default_factory=list)


class BattleStateUpdateRequest(BaseModel):
    """Manual update to battle state from frontend."""
    field: str
    value: Any
