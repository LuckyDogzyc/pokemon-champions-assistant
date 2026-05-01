from __future__ import annotations

import logging
import time

from app.schemas.battle_session import (
    BattleMon,
    BattleSession,
    MoveDetail,
    LogEntry,
    new_battle_session,
)
from app.schemas.recognition import BattlePhase, RecognitionStatePayload
from app.services.data_loader import load_base_stats, load_moves_index, load_pokemon_index
from app.services.name_matcher import NameMatcher

logger = logging.getLogger(__name__)

# ── Simple in-process move name DB (can be replaced with a full DB later) ──

_MOVE_NAME_TO_ID: dict[str, str] = {}


def _build_move_name_index() -> dict[str, str]:
    index: dict[str, str] = {}
    moves = load_moves_index()
    for move_id, info in moves.items():
        name = (info.get("name_zh") or info.get("name_en") or "").strip()
        if name:
            index[name] = move_id
    return index


def _lookup_move_detail(name: str) -> dict:
    """Look up a move's type/power/category/description by name.

    Returns a dict with keys: type, base_power, category, description.
    Missing fields get sensible defaults.
    """
    global _MOVE_NAME_TO_ID
    if not _MOVE_NAME_TO_ID:
        _MOVE_NAME_TO_ID.update(_build_move_name_index())

    move_id = _MOVE_NAME_TO_ID.get(name)
    if not move_id:
        return {}

    moves = load_moves_index()
    info = moves.get(move_id) or {}
    return {
        "type": info.get("type", "一般"),
        "base_power": int(info.get("base_power", 0)),
        "category": info.get("category", "Status"),
        "description": info.get("description", ""),
    }


# ── Base stat helpers ──

_POKEMON_INDEX_BY_NAME: dict[str, dict] | None = None


def _build_name_to_pokemon_index() -> dict[str, dict]:
    index = {}
    for entry in load_pokemon_index():
        name = entry.get("name_zh", "").strip()
        if name:
            index[name] = entry
    return index


def _lookup_pokemon(name: str) -> dict:
    """Look up a Pokémon's types and id by name."""
    global _POKEMON_INDEX_BY_NAME
    if _POKEMON_INDEX_BY_NAME is None:
        _POKEMON_INDEX_BY_NAME = _build_name_to_pokemon_index()

    entry = _POKEMON_INDEX_BY_NAME.get(name)
    if entry:
        return {
            "pokemon_id": entry.get("id", ""),
            "types": entry.get("types", []),
            "species": name,
        }
    return {}


def _lookup_base_stats(name: str) -> dict[str, int]:
    """Look up a Pokémon's base stats by name (uses NameMatcher to resolve id)."""
    matcher = NameMatcher()
    result = matcher.match(name)
    if not result.found or not result.pokemon_id:
        return {}
    return dict(load_base_stats().get(result.pokemon_id, {}))


# ── Store ──


class BattleSessionStore:
    """Manages the per-match BattleSession JSON object.

    The store is the single source of truth for battle data.
    UI reads from it; recognition pipeline writes to it.
    """

    def __init__(self) -> None:
        self._session: BattleSession = new_battle_session()

    # ── Read ──

    def get_session(self) -> BattleSession:
        return self._session

    # ── Lifecycle ──

    def reset_for_new_match(self) -> BattleSession:
        """Clear team/active/HP data but preserve the log.

        Called when settlement (FINAL_RESULT) is detected.
        """
        old_log = self._session.log
        self._session = new_battle_session()
        self._session.log = old_log
        # Mark the new session's reset timestamp so UI can detect the transition
        self._session.reset_timestamp = str(time.time())
        return self._session

    def force_reset_all(self) -> BattleSession:
        """Hard reset — everything including log.  Used by manual 'reset' button."""
        self._session = new_battle_session()
        return self._session

    # ── Team ──

    def _mon_from_name(self, name: str) -> BattleMon:
        """Create or lookup a BattleMon by name, enriching with known data."""
        # Check if this mon is already in the team (carry over item/gender)
        for mon in self._session.player_team + self._session.opponent_team:
            if mon.name == name:
                return mon

        # Otherwise build fresh
        pokemon_info = _lookup_pokemon(name)
        stats = _lookup_base_stats(name)
        return BattleMon(
            name=name,
            species=pokemon_info.get("species"),
            pokemon_id=pokemon_info.get("pokemon_id"),
            types=pokemon_info.get("types", []),
            base_stats=stats,
            level=50,
        )

    def set_player_team(self, slots: list[dict]) -> None:
        """Fill player team from RecognizedTeamSlot dicts.

        Only fills empty slots — does NOT overwrite already-set entries.
        """
        # Widen the list if needed (some slots may be None)
        for i, slot in enumerate(slots):
            name = slot.get("name") or slot.get("pokemon_name") or ""
            if not name:
                continue
            # Only fill if no entry at this position or entry has no name set
            if i < len(self._session.player_team) and self._session.player_team[i].name:
                continue
            mon = self._mon_from_name(name)
            # Override with slot-specific info
            if slot.get("item"):
                mon.item = slot["item"]
            if slot.get("gender"):
                mon.gender = slot["gender"]
            # Ensure list is long enough
            while len(self._session.player_team) <= i:
                self._session.player_team.append(BattleMon())
            self._session.player_team[i] = mon

    def set_opponent_team(self, slots: list[dict]) -> None:
        """Fill opponent team from RecognizedTeamSlot dicts."""
        for i, slot in enumerate(slots):
            name = slot.get("name") or slot.get("pokemon_name") or ""
            if not name:
                continue
            if i < len(self._session.opponent_team) and self._session.opponent_team[i].name:
                continue
            # For opponents we may not have full data — just store name
            mon = BattleMon(
                name=name,
                species=name,
                level=50,
            )
            if slot.get("gender"):
                mon.gender = slot["gender"]
            while len(self._session.opponent_team) <= i:
                self._session.opponent_team.append(BattleMon())
            self._session.opponent_team[i] = mon

    # ── Active mon ──

    def set_player_active(self, name: str) -> None:
        """Set the active player Pokémon by name.

        Looks up in player_team first; if found, copies that data in.
        If not found, creates a fresh BattleMon.
        """
        if not name:
            return

        # Try to find in team
        for mon in self._session.player_team:
            if mon.name == name:
                self._session.player_active = mon
                return

        # Not in team — create fresh
        mon = self._mon_from_name(name)
        self._session.player_active = mon

    def set_opponent_active(self, name: str) -> None:
        """Set the active opponent Pokémon by name."""
        if not name:
            return

        for mon in self._session.opponent_team:
            if mon.name == name:
                self._session.opponent_active = mon
                return

        mon = BattleMon(name=name, species=name, level=50)
        self._session.opponent_active = mon

    # ── HP ──

    def update_player_hp(self, current: int | None, max_hp: int | None) -> None:
        mon = self._session.player_active
        if current is not None:
            mon.current_hp = current
        if max_hp is not None:
            mon.max_hp = max_hp
        if mon.current_hp is not None and mon.max_hp is not None and mon.max_hp > 0:
            mon.current_hp_percent = round(mon.current_hp / mon.max_hp * 100, 1)
        if mon.current_hp is not None and mon.current_hp <= 0:
            mon.is_fainted = True

    def update_opponent_hp_by_percent(self, percent: float | None) -> None:
        mon = self._session.opponent_active
        if percent is None:
            return
        mon.current_hp_percent = round(percent, 1)
        if percent <= 0:
            mon.is_fainted = True

    # ── Moves ──

    def set_player_moves(self, moves: list[dict]) -> None:
        """Set the moves for the currently active player Pokémon.

        Each dict from MoveListRecognizer has fields: name, pp_current, pp_max.
        Enriches each move with type/base_power/category/description from move DB.
        """
        if not moves:
            return

        mon = self._session.player_active
        enriched: list[MoveDetail] = []
        revealed: list[str] = []

        for move_dict in moves:
            name = (move_dict.get("name") or "").strip()
            if not name:
                continue

            revealed.append(name)

            # Look up from DB
            detail = _lookup_move_detail(name)
            enriched.append(
                MoveDetail(
                    name=name,
                    type=detail.get("type", "一般"),
                    category=detail.get("category", "Status"),
                    base_power=int(detail.get("base_power", 0)),
                    pp_current=move_dict.get("pp_current"),
                    pp_max=move_dict.get("pp_max"),
                    description=detail.get("description", ""),
                )
            )

        if enriched:
            mon.moves = enriched
        if revealed:
            # Merge without duplicates
            existing = set(mon.revealed_move_names)
            for r in revealed:
                if r not in existing:
                    mon.revealed_move_names.append(r)
                    existing.add(r)

    # ── Log ──

    def append_log(self, entry_type: str, text: str, *, timestamp: str | None = None) -> None:
        if timestamp is None:
            timestamp = str(time.time())
        self._session.log.append(
            LogEntry(type=entry_type, text=text, timestamp=timestamp)
        )

    def append_log_batch(self, entries: list[dict]) -> None:
        for entry in entries:
            self.append_log(
                entry.get("type", "info"),
                entry.get("text", ""),
                timestamp=entry.get("timestamp"),
            )

    # ── Lifecycle helpers ──

    def mark_over(self) -> None:
        self._session.is_over = True

    # ── Sync from RecognitionStatePayload ──

    def sync_from_recognition(self, result: RecognitionStatePayload) -> None:
        """Synchronize the BattleSession from a recognition result.

        Called by the RecognizeScheduler's loop after each recognition cycle.
        """
        phase = result.current_phase

        # ── Team select: fill team rosters ──
        if phase == BattlePhase.TEAM_SELECT:
            player_slots = [s.model_dump() for s in result.player_team_slots if s.name]
            opponent_slots = [s.model_dump() for s in result.opponent_team_slots if s.name]
            if player_slots:
                self.set_player_team(player_slots)
            if opponent_slots:
                self.set_opponent_team(opponent_slots)

        # ── Battle phase: set active mon, HP, moves ──
        if phase == BattlePhase.BATTLE:
            player_name = result.player.name
            opponent_name = result.opponent.name

            if player_name:
                self.set_player_active(player_name)
            if opponent_name:
                self.set_opponent_active(opponent_name)

            if result.player_hp_current is not None or result.player_hp_max is not None:
                self.update_player_hp(result.player_hp_current, result.player_hp_max)
            if result.opponent_hp_percent is not None:
                self.update_opponent_hp_by_percent(result.opponent_hp_percent)

            if result.revealed_moves:
                self.set_player_moves(
                    [dict(m) for m in result.revealed_moves]
                )

        # ── FINAL_RESULT: mark over ──
        if phase == BattlePhase.FINAL_RESULT:
            if not self._session.is_over:
                self.mark_over()

        # ── TEAM_SELECT after FINAL_RESULT: reset for next match, preserving log ──
        if phase == BattlePhase.TEAM_SELECT and self._session.is_over:
            self.reset_for_new_match()
            # Now fill team as usual
            player_slots = [s.model_dump() for s in result.player_team_slots if s.name]
            opponent_slots = [s.model_dump() for s in result.opponent_team_slots if s.name]
            if player_slots:
                self.set_player_team(player_slots)
            if opponent_slots:
                self.set_opponent_team(opponent_slots)
