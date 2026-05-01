from __future__ import annotations

import time

from pydantic import BaseModel, Field


class MoveDetail(BaseModel):
    """A single move with full detail for display."""

    name: str = ""
    type: str = "一般"
    category: str = "Status"  # Physical | Special | Status
    base_power: int = 0
    pp_current: int | None = None
    pp_max: int | None = None
    description: str = ""


class BattleMon(BaseModel):
    """A single Pokémon with full battle-time data."""

    name: str | None = None
    species: str | None = None
    pokemon_id: str | None = None
    types: list[str] = []
    base_stats: dict[str, int] = Field(default_factory=dict)
    # {hp, attack, defense, sp_attack, sp_defense, speed}

    item: str | None = None
    gender: str | None = None
    level: int = 50

    current_hp: int | None = None
    max_hp: int | None = None
    current_hp_percent: float | None = None

    status: list[str] = Field(default_factory=list)
    stat_stages: dict[str, int] = Field(
        default_factory=lambda: {
            "attack": 0,
            "defense": 0,
            "sp_attack": 0,
            "sp_defense": 0,
            "speed": 0,
            "accuracy": 0,
            "evasion": 0,
        }
    )
    buffs: list[str] = Field(default_factory=list)
    debuffs: list[str] = Field(default_factory=list)

    moves: list[MoveDetail] = Field(default_factory=list)
    revealed_move_names: list[str] = Field(default_factory=list)

    is_fainted: bool = False
    turns_on_field: int = 0


class LogEntry(BaseModel):
    type: str = "info"  # round | send | move | switch | status_change | faint | info | dialog
    text: str = ""
    timestamp: str = ""


class BattleSession(BaseModel):
    """Per-match battle data model.

    One session per match.  The UI reads everything from this model.
    On settlement (FINAL_RESULT) the session is *mostly* cleared —
    only the log list is preserved so the user can review past actions.
    """

    battle_id: str = ""
    turn: int = 1

    player_active: BattleMon = Field(default_factory=BattleMon)
    opponent_active: BattleMon = Field(default_factory=BattleMon)

    player_team: list[BattleMon] = Field(default_factory=list)
    opponent_team: list[BattleMon] = Field(default_factory=list)

    log: list[LogEntry] = Field(default_factory=list)

    is_over: bool = False
    reset_timestamp: str | None = None


def new_battle_session() -> BattleSession:
    """Create a fresh BattleSession with a unique id."""
    return BattleSession(
        battle_id=f"battle-{int(time.time() * 1000)}",
        turn=1,
        is_over=False,
        log=[],
    )
