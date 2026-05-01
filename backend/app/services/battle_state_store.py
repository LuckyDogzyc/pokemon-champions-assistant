from __future__ import annotations

import time
import uuid
from typing import Any

from app.schemas.battle_state import (
    BattleState,
    FieldCondition,
    MonBattleState,
    StatusCondition,
    TeamEntry,
)
from app.schemas.phase import BattlePhase
from app.schemas.recognition import RecognitionStatePayload


class BattleStateStore:
    """In-memory tracker that accumulates battle state from OCR recognition results.

    Design:
    - Updated each recognition cycle from RecognitionPipeline output
    - Records field conditions, stat stages, HP history, revealed moves
    - Provides the current full snapshot for API consumption
    - Reset on new battle start
    """

    def __init__(self) -> None:
        self._state = BattleState(battle_id="")
        self._started = False

    def _new_battle_id(self) -> str:
        return f"battle-{uuid.uuid4().hex[:8]}-{int(time.time())}"

    def reset(self) -> BattleState:
        """Reset state for a new battle."""
        self._state = BattleState(battle_id=self._new_battle_id())
        self._started = True
        return self._state

    @property
    def state(self) -> BattleState:
        return self._state

    def update_from_recognition(self, payload: RecognitionStatePayload) -> BattleState:
        """Feed the latest recognition result and update tracked state.

        This is the main entry point called each poll cycle.
        """
        phase = str(payload.current_phase)

        # Detect battle start: transition from non-battle to team_select or battle
        if phase in (BattlePhase.TEAM_SELECT, BattlePhase.BATTLE) and not self._started:
            self.reset()

        # Detect battle end: transition from battle to unknown with no active names
        if self._started and phase == BattlePhase.UNKNOWN:
            if not payload.player.name and not payload.opponent.name:
                self._started = False
                return self._state

        if not self._started:
            return self._state

        self._state.phase = phase

        # Update active mons
        self._update_active_mon("player", payload)
        self._update_active_mon("opponent", payload)

        # Track HP history
        self._record_hp_snapshot(payload)

        # Track revealed moves from ROI payloads or directly from payload
        if payload.revealed_moves:
            self._update_revealed_moves_v2(payload.revealed_moves)
        else:
            self._update_revealed_moves(payload)

        # Update team roster from team_preview if available
        if payload.team_preview:
            self._update_team_from_preview(payload)

        # 全流程追踪 v2：检测阵容锁定
        if payload.locked_in:
            self._lock_team()
            self._state._locked_in = True  # type: ignore

        # 全流程追踪 v2：更新队伍 slot 数据（放在锁定之后，触发时重新锁定）
        if payload.player_team_slots:
            self._update_team_from_slots(payload)

        # 如果之前已锁定，且队伍刚被重新创建，重新应用锁定
        if getattr(self._state, '_locked_in', False) and self._state.player_team:
            self._lock_team()

        # Increment turn on phase transitions
        if phase == BattlePhase.MOVE_RESOLUTION:
            self._state.turn += 1

        return self._state

    def _update_active_mon(self, side: str, payload: RecognitionStatePayload) -> None:
        recognized = payload.player if side == "player" else payload.opponent
        target: MonBattleState = (
            self._state.player_active if side == "player" else self._state.opponent_active
        )

        name = recognized.name
        if name and name != target.name:
            # Pokémon switched in — record previous as revealed
            if target.name and target.revealed_moves:
                self._record_switch_out(side, target)
            # Reset stat stages on switch
            target.name = name
            target.stat_stages = target.stat_stages.model_construct(
                attack=0, defense=0, sp_attack=0, sp_defense=0,
                speed=0, accuracy=0, evasion=0,
            )
            target.status = StatusCondition.NONE
            target.turns_on_field = 0

        # Update HP from ROI payloads (原有逻辑)
        roi_payloads = payload.roi_payloads or {}
        panel_key = f"{side}_status_panel"
        panel = roi_payloads.get(panel_key, {})
        if isinstance(panel, dict):
            hp_text = panel.get("hp_text")
            if hp_text and isinstance(hp_text, str):
                target.current_hp_percent = self._parse_hp_percent(hp_text)
            status_text = panel.get("status_text")
            if status_text and isinstance(status_text, str):
                target.status = self._parse_status(status_text)

        # 全流程追踪 v2：从 payload 新字段更新 HP
        if side == "player":
            if payload.player_hp_current is not None and payload.player_hp_max is not None and payload.player_hp_max > 0:
                target.current_hp_percent = round(payload.player_hp_current / payload.player_hp_max * 100, 1)
        elif side == "opponent":
            if payload.opponent_hp_percent is not None:
                target.current_hp_percent = payload.opponent_hp_percent

        if name:
            target.turns_on_field += 1

    def _parse_hp_percent(self, hp_text: str) -> float | None:
        """Parse HP text like '85/100' or '85%' into a percentage."""
        hp_text = hp_text.strip().strip("%")
        if "/" in hp_text:
            parts = hp_text.split("/")
            try:
                current = float(parts[0])
                maximum = float(parts[1])
                if maximum > 0:
                    return round(current / maximum * 100, 1)
            except (ValueError, IndexError):
                pass
            return None
        try:
            return float(hp_text)
        except ValueError:
            return None

    def _parse_status(self, status_text: str) -> StatusCondition:
        mapping = {
            "毒": StatusCondition.POISON,
            "猛毒": StatusCondition.BAD_POISON,
            "火伤": StatusCondition.BURN,
            "麻痹": StatusCondition.PARALYSIS,
            "睡眠": StatusCondition.SLEEP,
            "冰冻": StatusCondition.FREEZE,
            "混乱": StatusCondition.CONFUSION,
        }
        return mapping.get(status_text.strip(), StatusCondition.NONE)

    def _record_hp_snapshot(self, payload: RecognitionStatePayload) -> None:
        """Record HP percentages for change detection."""
        player_hp = self._state.player_active.current_hp_percent
        opponent_hp = self._state.opponent_active.current_hp_percent
        timestamp = payload.timestamp

        self._state.hp_history.append({
            "timestamp": timestamp,
            "player_hp": player_hp,
            "opponent_hp": opponent_hp,
            "turn": self._state.turn,
        })

        # Trim history to last 100 entries
        if len(self._state.hp_history) > 100:
            self._state.hp_history = self._state.hp_history[-100:]

    def _update_revealed_moves(self, payload: RecognitionStatePayload) -> None:
        """Extract move names from OCR and record them as revealed."""
        roi_payloads = payload.roi_payloads or {}
        move_list = roi_payloads.get("move_list", {})
        if not isinstance(move_list, dict):
            return

        moves = move_list.get("moves")
        if not isinstance(moves, list):
            return

        for move in moves:
            move_name = None
            if isinstance(move, dict):
                move_name = move.get("name") or move.get("text")
            elif isinstance(move, str):
                move_name = move
            if move_name and isinstance(move_name, str) and move_name.strip():
                revealed = self._state.player_active.revealed_moves
                if move_name.strip() not in revealed:
                    revealed.append(move_name.strip())

    def _update_team_from_preview(self, payload: RecognitionStatePayload) -> None:
        """Update team roster from team_preview data."""
        preview = payload.team_preview
        if not preview:
            return

        if preview.player_team:
            self._state.player_team = [
                TeamEntry(name=name, is_active=False, is_fainted=False)
                for name in preview.player_team
            ]
        if preview.opponent_team:
            self._state.opponent_team = [
                TeamEntry(name=name, is_active=False, is_fainted=False)
                for name in preview.opponent_team
            ]

    def _update_team_from_slots(self, payload: RecognitionStatePayload) -> None:
        """Update team roster from recognized team slots (全流程追踪 v2)."""
        player_entries = []
        for slot in payload.player_team_slots:
            entry = TeamEntry(
                name=slot.name,
                pokemon_id=slot.sprite_match_id,
                is_active=False,
                item=slot.item,
                gender=slot.gender,
            )
            player_entries.append(entry)
        if any(e.name for e in player_entries):
            self._state.player_team = player_entries

        opponent_entries = []
        for slot in payload.opponent_team_slots:
            entry = TeamEntry(
                name=slot.name,
                pokemon_id=slot.sprite_match_id,
                is_active=False,
                item=slot.item,
                gender=slot.gender,
            )
            opponent_entries.append(entry)
        if any(e.name for e in opponent_entries):
            self._state.opponent_team = opponent_entries

    def _lock_team(self) -> None:
        """Mark the first 3 player team entries as active (阵容锁定)."""
        for i, entry in enumerate(self._state.player_team):
            entry.is_active = i < 3

    def _update_revealed_moves_v2(self, revealed_moves: list[dict]) -> None:
        """Update revealed moves from the new revealed_moves payload."""
        current_names = self._state.player_active.revealed_moves
        for move in revealed_moves:
            move_name = move.get("name") if isinstance(move, dict) else None
            if move_name and isinstance(move_name, str) and move_name.strip():
                if move_name.strip() not in current_names:
                    current_names.append(move_name.strip())

    def _record_switch_out(self, side: str, mon: MonBattleState) -> None:
        """Record that a mon switched out — add to move log."""
        self._state.move_log.append({
            "type": "switch_out",
            "side": side,
            "name": mon.name,
            "revealed_moves": list(mon.revealed_moves),
            "turn": self._state.turn,
        })

    def manual_update(self, field: str, value: Any) -> BattleState:
        """Apply a manual override from the frontend."""
        parts = field.split(".")
        obj = self._state
        for part in parts[:-1]:
            obj = getattr(obj, part, None)
            if obj is None:
                return self._state
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
        return self._state
