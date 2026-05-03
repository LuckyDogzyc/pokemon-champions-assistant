from __future__ import annotations

import pytest

from app.schemas.phase import BattlePhase
from app.schemas.recognition import (
    RecognitionSource,
    RecognitionStatePayload,
    RecognizedSide,
    RecognizedTeamSlot,
)
from app.services.battle_session_store import BattleSessionStore


def _payload(phase: BattlePhase, **kwargs) -> RecognitionStatePayload:
    return RecognitionStatePayload(current_phase=phase, timestamp="test-ts", **kwargs)


def _slot(name: str | None = None, *, item: str | None = None, gender: str | None = None) -> RecognizedTeamSlot:
    return RecognizedTeamSlot(name=name, item=item, gender=gender)


def test_team_select_preserves_slot_order_and_enriches_both_teams() -> None:
    store = BattleSessionStore()

    result = _payload(
        BattlePhase.TEAM_SELECT,
        player_team_slots=[
            _slot("皮卡丘", item="电气球", gender="male"),
            _slot(None),
            _slot("振翼发", item="爽喉喷雾", gender="female"),
            _slot(None),
            _slot(None),
            _slot(None),
        ],
        opponent_team_slots=[
            _slot(None),
            _slot("皮卡丘"),
            _slot(None),
            _slot(None),
            _slot(None),
            _slot(None),
        ],
    )

    store.sync_from_recognition(result)
    session = store.get_session()

    assert len(session.player_team) >= 3
    assert session.player_team[0].name == "皮卡丘"
    assert session.player_team[0].item == "电气球"
    assert session.player_team[0].gender == "male"
    assert session.player_team[0].base_stats
    assert session.player_team[1].name is None
    assert session.player_team[2].name == "振翼发"
    assert session.player_team[2].item == "爽喉喷雾"
    assert session.player_team[2].gender == "female"

    assert len(session.opponent_team) >= 2
    assert session.opponent_team[0].name is None
    assert session.opponent_team[1].name == "皮卡丘"
    assert session.opponent_team[1].base_stats
    assert session.opponent_team[1].types


def test_battle_phase_updates_active_hp_moves_and_status() -> None:
    store = BattleSessionStore()
    store.sync_from_recognition(
        _payload(
            BattlePhase.TEAM_SELECT,
            player_team_slots=[_slot("皮卡丘"), _slot(), _slot(), _slot(), _slot(), _slot()],
            opponent_team_slots=[_slot("振翼发"), _slot(), _slot(), _slot(), _slot(), _slot()],
        )
    )

    store.sync_from_recognition(
        _payload(
            BattlePhase.BATTLE,
            player=RecognizedSide(name="皮卡丘", confidence=0.99, source=RecognitionSource.OCR),
            opponent=RecognizedSide(name="振翼发", confidence=0.98, source=RecognitionSource.OCR),
            player_hp_current=145,
            player_hp_max=167,
            opponent_hp_percent=62.5,
            revealed_moves=[
                {"name": "Flamethrower", "pp_current": 10, "pp_max": 15},
                {"name": "Shadow Ball", "pp_current": 8, "pp_max": 15},
            ],
            roi_payloads={
                "player_status_panel": {"status_abnormality": "burn"},
                "opponent_status_panel": {"status_abnormality": "poison"},
            },
        )
    )

    session = store.get_session()
    assert session.player_active.name == "皮卡丘"
    assert session.player_active.current_hp == 145
    assert session.player_active.max_hp == 167
    assert session.player_active.current_hp_percent == pytest.approx(86.8)
    assert "burn" in session.player_active.status

    assert session.opponent_active.name == "振翼发"
    assert session.opponent_active.current_hp_percent == 62.5
    assert "poison" in session.opponent_active.status

    assert [move.name for move in session.player_active.moves] == ["Flamethrower", "Shadow Ball"]
    assert session.player_active.moves[0].type == "Fire"
    assert session.player_active.moves[0].category == "Special"
    assert session.player_active.moves[0].base_power == 90
    assert session.player_active.moves[0].pp_current == 10
    assert session.player_active.moves[0].pp_max == 15


def test_final_result_freezes_session_and_next_team_select_starts_new_match_preserving_log() -> None:
    store = BattleSessionStore()
    store.sync_from_recognition(
        _payload(
            BattlePhase.TEAM_SELECT,
            player_team_slots=[_slot("皮卡丘"), _slot(), _slot(), _slot(), _slot(), _slot()],
        )
    )
    store.sync_from_recognition(
        _payload(
            BattlePhase.BATTLE,
            player=RecognizedSide(name="皮卡丘", confidence=0.99, source=RecognitionSource.OCR),
            player_hp_current=10,
            player_hp_max=100,
        )
    )
    store.append_log("move", "皮卡丘 使用了十万伏特", timestamp="1")

    store.sync_from_recognition(_payload(BattlePhase.FINAL_RESULT))
    finished = store.get_session()
    assert finished.is_over is True
    assert finished.player_active.name == "皮卡丘"
    assert [entry.text for entry in finished.log] == ["皮卡丘 使用了十万伏特"]

    old_battle_id = finished.battle_id
    store.sync_from_recognition(
        _payload(
            BattlePhase.TEAM_SELECT,
            player_team_slots=[_slot("振翼发"), _slot(), _slot(), _slot(), _slot(), _slot()],
        )
    )
    next_session = store.get_session()
    assert next_session.battle_id != old_battle_id
    assert next_session.is_over is False
    assert next_session.player_active.name is None
    assert next_session.player_team[0].name == "振翼发"
    assert [entry.text for entry in next_session.log] == ["皮卡丘 使用了十万伏特"]
