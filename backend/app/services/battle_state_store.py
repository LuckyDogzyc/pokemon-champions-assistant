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


# ── Battle log entry types ──
LOG_SEND_OUT = "send_out"
LOG_USE_MOVE = "use_move"
LOG_STATUS_CHANGE = "status_change"
LOG_HP_CHANGE = "hp_change"
LOG_TURN = "turn"
LOG_SWITCH = "switch"
LOG_FAINT = "faint"
LOG_EFFECTIVENESS = "effectiveness"


def _make_log(entry_type: str, **kw: Any) -> dict[str, Any]:
    return {"type": entry_type, "timestamp": time.time(), **kw}


class BattleStateStore:
    """In-memory tracker that accumulates battle state from OCR recognition results.

    Design:
    - Updated each recognition cycle from RecognitionPipeline output
    - Records field conditions, stat stages, HP history, revealed moves
    - Auto-generates battle log entries from detected changes
    - Provides the current full snapshot for API consumption
    - Reset on new battle start
    """

    def __init__(self) -> None:
        self._state = BattleState(battle_id="")
        self._started = False
        # Track previous values for change detection
        self._prev_player_hp: float | None = None
        self._prev_opponent_hp: float | None = None
        self._prev_player_status: StatusCondition | None = None
        self._prev_player_name: str | None = None
        self._prev_opponent_name: str | None = None
        self._prev_moves: list[str] = []
        self._hp_sample_count: int = 0
        self._last_battle_id: str = ""  # Track previous battle_id to detect resets
        # 结算检测：记录上一个 phase，用于检测 phase 过渡
        self._prev_phase: str | None = None
        # 去重复缓存：event_hash → timestamp
        self._recent_events: dict[str, float] = {}
        self._dedup_window: float = 5.0  # seconds

    def _new_battle_id(self) -> str:
        return f"battle-{uuid.uuid4().hex[:8]}-{int(time.time())}"

    def reset(self) -> BattleState:
        """Reset state for a new battle."""
        self._last_battle_id = self._state.battle_id
        self._state = BattleState(battle_id=self._new_battle_id())
        self._started = True
        self._prev_player_hp = None
        self._prev_opponent_hp = None
        self._prev_player_status = None
        self._prev_player_name = None
        self._prev_opponent_name = None
        self._prev_moves = []
        self._hp_sample_count = 0
        self._prev_phase = None
        self._recent_events.clear()
        return self._state

    def was_just_reset(self) -> bool:
        """Returns True if the last reset() call created a new battle_id.

        Used by the API layer to signal 'battle_reset' to the frontend.
        """
        return self._state.battle_id != self._last_battle_id

    @property
    def state(self) -> BattleState:
        return self._state

    def update_from_recognition(self, payload: RecognitionStatePayload) -> BattleState:
        """Feed the latest recognition result and update tracked state."""
        phase = str(payload.current_phase)

        # Detect battle start: transition from non-battle to team_select or battle
        if phase in (BattlePhase.TEAM_SELECT, BattlePhase.BATTLE) and not self._started:
            self.reset()

        # === 结算检测 ===
        # 从战斗/battle 过渡到 final_result 时触发自动清除
        if self._started and phase == BattlePhase.FINAL_RESULT:
            if self._prev_phase and self._prev_phase in (BattlePhase.BATTLE, BattlePhase.TEAM_SELECT):
                # 触发清除 — 记录一条结算日志再 reset
                self._state.phase = phase
                log_entry = _make_log(LOG_TURN, turn=self._state.turn + 1,
                              text="对局结束")
                if not self._is_duplicate_event(log_entry):
                    self._state.move_log.append(log_entry)
                self._state = self.reset()
                self._started = False
                return self._state
            # 如果已经在结算阶段了（持续检测到），不再重复清除
            self._prev_phase = phase
            return self._state

        # Detect battle end via UNKNOWN (old logic, keep as supplementary)
        if self._started and phase == BattlePhase.UNKNOWN:
            if not payload.player.name and not payload.opponent.name:
                self._started = False
                self._prev_phase = phase
                return self._state

        if not self._started:
            self._prev_phase = phase
            return self._state

        self._state.phase = phase

        # Update active mons (this also detects switches)
        self._update_active_mon("player", payload)
        self._update_active_mon("opponent", payload)

        # Track HP history and generate HP change logs
        self._record_hp_snapshot(payload)

        # Track revealed moves
        if payload.revealed_moves:
            self._update_revealed_moves_v2(payload.revealed_moves)
        else:
            self._update_revealed_moves(payload)

        # Detect new moves used from move_slot data
        self._detect_move_usage(payload)

        # Update team roster
        if payload.team_preview:
            self._update_team_from_preview(payload)

        # 全流程追踪 v2：检测阵容锁定
        if payload.locked_in:
            self._lock_team()
            self._state._locked_in = True  # type: ignore

        if payload.player_team_slots:
            self._update_team_from_slots(payload)

        if getattr(self._state, '_locked_in', False) and self._state.player_team:
            self._lock_team()

        # Increment turn
        if phase == BattlePhase.MOVE_RESOLUTION:
            self._state.turn += 1
            p_name = self._state.player_active.name or "???";
            o_name = self._state.opponent_active.name or "???";
            log_entry = _make_log(LOG_TURN, turn=self._state.turn, text=f"第 {self._state.turn} 回合")
            if not self._is_duplicate_event(log_entry):
                self._state.move_log.append(log_entry)

        return self._state

    def _update_active_mon(self, side: str, payload: RecognitionStatePayload) -> None:
        recognized = payload.player if side == "player" else payload.opponent
        target: MonBattleState = (
            self._state.player_active if side == "player" else self._state.opponent_active
        )

        name = recognized.name
        prev_name = self._prev_player_name if side == "player" else self._prev_opponent_name

        if name and name != target.name:
            # Pokémon switched in
            if target.name:
                self._record_switch_out(side, target)
                log_entry = _make_log(LOG_SWITCH, side=side, name=target.name,
                              text=f"{'我方' if side == 'player' else '对方'} {target.name} 退场")
                if not self._is_duplicate_event(log_entry):
                    self._state.move_log.append(log_entry)
            target.name = name
            target.stat_stages = target.stat_stages.model_construct(
                attack=0, defense=0, sp_attack=0, sp_defense=0,
                speed=0, accuracy=0, evasion=0,
            )
            target.status = StatusCondition.NONE
            target.turns_on_field = 0
            log_entry = _make_log(LOG_SEND_OUT, side=side, name=name,
                          text=f"{'我方' if side == 'player' else '对方'} 派出了 {name}")
            if not self._is_duplicate_event(log_entry):
                self._state.move_log.append(log_entry)

        # Update HP
        hp_panel = (payload.roi_payloads or {}).get(f"{side}_status_panel", {})
        if isinstance(hp_panel, dict):
            hp_text = hp_panel.get("hp_text")
            if hp_text and isinstance(hp_text, str):
                target.current_hp_percent = self._parse_hp_percent(hp_text)

        if side == "player":
            if payload.player_hp_current is not None and payload.player_hp_max is not None and payload.player_hp_max > 0:
                target.current_hp_percent = round(payload.player_hp_current / payload.player_hp_max * 100, 1)
        elif side == "opponent":
            if payload.opponent_hp_percent is not None:
                target.current_hp_percent = payload.opponent_hp_percent

        # Detect status changes
        status_text = hp_panel.get("status_abnormality") if isinstance(hp_panel, dict) else None
        if status_text and isinstance(status_text, str):
            parsed_status = self._parse_status(status_text)
            if parsed_status != StatusCondition.NONE and parsed_status != target.status:
                if target.name:
                    log_entry = _make_log(LOG_STATUS_CHANGE, side=side, name=target.name, status=status_text,
                                  text=f"{target.name} {status_text}了")
                    if not self._is_duplicate_event(log_entry):
                        self._state.move_log.append(log_entry)
                target.status = parsed_status

        if name:
            target.turns_on_field += 1

        # Update prev tracking
        if side == "player":
            self._prev_player_name = target.name
            self._prev_player_status = target.status
        else:
            self._prev_opponent_name = target.name

    def _detect_move_usage(self, payload: RecognitionStatePayload) -> None:
        """Detect new moves used from move_slot data and detect HP drops."""
        rois = payload.roi_payloads or {}
        new_moves: list[str] = []

        for i in range(1, 5):
            slot = rois.get(f"move_slot_{i}")
            if isinstance(slot, dict):
                name = slot.get("pokemon_name") or (slot.get("recognized_texts") or [None])[0]
                if name and isinstance(name, str) and name not in new_moves:
                    new_moves.append(name)

        # If we have a player name and the move list changed, log the first new move
        player_name = self._state.player_active.name
        if player_name and new_moves:
            if set(new_moves) != set(self._prev_moves):
                newly_detected = [m for m in new_moves if m not in self._prev_moves]
                if newly_detected:
                    move_name = newly_detected[-1]
                    log_entry = _make_log(LOG_USE_MOVE, side="player", name=player_name, move=move_name,
                                  text=f"我方 {player_name} 使用了 {move_name}")
                    if not self._is_duplicate_event(log_entry):
                        self._state.move_log.append(log_entry)
            self._prev_moves = new_moves

    def _parse_hp_percent(self, hp_text: str) -> float | None:
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
            "中毒": StatusCondition.POISON,
            "烧伤": StatusCondition.BURN,
            "麻痹": StatusCondition.PARALYSIS,
        }
        for key, val in mapping.items():
            if key in status_text:
                return val
        return StatusCondition.NONE

    def _record_hp_snapshot(self, payload: RecognitionStatePayload) -> None:
        player_hp = self._state.player_active.current_hp_percent
        opponent_hp = self._state.opponent_active.current_hp_percent
        timestamp = payload.timestamp

        self._state.hp_history.append({
            "timestamp": timestamp,
            "player_hp": player_hp,
            "opponent_hp": opponent_hp,
            "turn": self._state.turn,
        })

        # Detect significant HP changes (skip first few samples to stabilize)
        self._hp_sample_count += 1
        if self._hp_sample_count > 3:
            p_name = self._state.player_active.name
            o_name = self._state.opponent_active.name

            if player_hp is not None and self._prev_player_hp is not None:
                drop = self._prev_player_hp - player_hp
                if drop > 10 and p_name:
                    log_entry = _make_log(LOG_HP_CHANGE, side="player", name=p_name,
                                  hp_drop=round(drop, 1),
                                  text=f"{p_name} 受到了伤害! HP {round(player_hp)}%")
                    if not self._is_duplicate_event(log_entry):
                        self._state.move_log.append(log_entry)
            if opponent_hp is not None and self._prev_opponent_hp is not None:
                drop = self._prev_opponent_hp - opponent_hp
                if drop > 10 and o_name:
                    log_entry = _make_log(LOG_HP_CHANGE, side="opponent", name=o_name,
                                  hp_drop=round(drop, 1),
                                  text=f"对方 {o_name} 受到了伤害! HP {round(opponent_hp)}%")
                    if not self._is_duplicate_event(log_entry):
                        self._state.move_log.append(log_entry)

        self._prev_player_hp = player_hp
        self._prev_opponent_hp = opponent_hp

        # Trim
        if len(self._state.hp_history) > 100:
            self._state.hp_history = self._state.hp_history[-100:]
            # Also trim move_log to keep it manageable
            log_entries = [e for e in self._state.move_log if e.get("type") != LOG_HP_CHANGE]
            hp_logs = [e for e in self._state.move_log if e.get("type") == LOG_HP_CHANGE]
            if len(hp_logs) > 30:
                hp_logs = hp_logs[-30:]
            self._state.move_log = log_entries + hp_logs

    def _update_revealed_moves(self, payload: RecognitionStatePayload) -> None:
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
        for i, entry in enumerate(self._state.player_team):
            entry.is_active = i < 3

    def _update_revealed_moves_v2(self, revealed_moves: list[dict]) -> None:
        current_names = self._state.player_active.revealed_moves
        for move in revealed_moves:
            move_name = move.get("name") if isinstance(move, dict) else None
            if move_name and isinstance(move_name, str) and move_name.strip():
                if move_name.strip() not in current_names:
                    current_names.append(move_name.strip())

    def _record_switch_out(self, side: str, mon: MonBattleState) -> None:
        log_entry = _make_log(LOG_SWITCH, side=side, name=mon.name,
                      text=f"{'我方' if side == 'player' else '对方'} {mon.name} 退场")
        if not self._is_duplicate_event(log_entry):
            self._state.move_log.append(log_entry)

    def _is_duplicate_event(self, log_entry: dict[str, Any]) -> bool:
        """Check if a log entry is a duplicate within the dedup window.

        Generates a hash from the entry type and key fields (side, name,
        move, etc.) and checks if the same hash was recorded recently.
        """
        now = time.time()
        # Prune expired entries
        expired = [h for h, ts in self._recent_events.items() if now - ts > self._dedup_window]
        for h in expired:
            self._recent_events.pop(h, None)

        # Build event hash from type + significant fields
        parts = [str(log_entry.get('type', ''))]
        for key in ('side', 'name', 'move', 'status', 'hp_drop'):
            val = log_entry.get(key)
            if val is not None:
                parts.append(f'{key}={val}')
        event_hash = '|'.join(parts)

        if event_hash in self._recent_events:
            return True
        self._recent_events[event_hash] = now
        return False

    def manual_update(self, field: str, value: Any) -> BattleState:
        parts = field.split(".")
        obj = self._state
        for part in parts[:-1]:
            obj = getattr(obj, part, None)
            if obj is None:
                return self._state
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
        return self._state
