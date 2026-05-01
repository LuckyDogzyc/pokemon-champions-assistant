"""Tests for the full battle flow tracking v2 features.

Tests cover:
1. TeamSelectRecognizer — slot recognition
2. MoveListRecognizer — move + PP recognition
3. recognition_pipeline — new team_select ROI payloads (player_mon_1~6, opponent_mon_1~6)
4. recognition_pipeline — new battle ROI payloads (HP areas, move slots)
5. RecognitionStatePayload — serialization of new fields
6. battle_state_store — team slot updates + roster locking
"""

from __future__ import annotations

import base64

from app.schemas.phase import BattlePhase
from app.schemas.recognition import (
    RecognizedSide,
    RecognizedTeamSlot,
    RecognitionStatePayload,
    RecognitionSource,
    TeamPreviewState,
)
from app.services.battle_state_store import BattleStateStore
from app.services.layout_anchors import DEFAULT_LAYOUTS
from app.services.recognition_pipeline import RecognitionPipeline, build_roi_payloads


def _make_preview_data_url(width=200, height=100):
    """Generate a minimal preview data URL for testing."""
    header = f'P6\n{width} {height}\n255\n'.encode('ascii')
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels.extend(((x * 3) % 256, (y * 5) % 256, ((x + y) * 7) % 256))
    return 'data:image/x-portable-pixmap;base64,' + base64.b64encode(header + bytes(pixels)).decode('ascii')


# ── Test 1: Layout anchors contain new team_select anchors ──


def test_team_select_layout_has_player_mon_anchors():
    """team_select_default should have 6 player_mon anchors."""
    anchors = DEFAULT_LAYOUTS.get('team_select_default', {})
    for i in range(1, 7):
        key = f'player_mon_{i}'
        assert key in anchors, f'Missing anchor: {key}'


def test_team_select_layout_has_opponent_mon_anchors():
    """team_select_default should have 6 opponent_mon anchors."""
    anchors = DEFAULT_LAYOUTS.get('team_select_default', {})
    for i in range(1, 7):
        key = f'opponent_mon_{i}'
        assert key in anchors, f'Missing anchor: {key}'


# ── Test 2: Build ROI payloads returns new anchors ──


def test_build_roi_payloads_returns_all_team_slots():
    """build_roi_payloads for team_select should return 12 slot payloads."""
    frame = {
        'width': 1920,
        'height': 1080,
        'layout_variant': 'team_select_default',
        'preview_image_data_url': _make_preview_data_url(),
    }
    payloads = build_roi_payloads(frame, phase=BattlePhase.TEAM_SELECT, layout_variant='team_select_default')

    # instruction_banner should still be there
    assert 'instruction_banner' in payloads

    # All 6 player_mon payloads
    for i in range(1, 7):
        key = f'player_mon_{i}'
        assert key in payloads, f'Missing {key}'
        assert payloads[key]['role'] == f'team-select-player-slot-{i}', f'Wrong role for {key}'
        assert payloads[key]['source'] == 'roi-source-frame'

    # All 6 opponent_mon payloads
    for i in range(1, 7):
        key = f'opponent_mon_{i}'
        assert key in payloads, f'Missing {key}'
        assert payloads[key]['role'] == f'team-select-opponent-slot-{i}', f'Wrong role for {key}'
        assert payloads[key]['source'] == 'roi-source-frame'


# ── Test 3: Battle layout has new HP + move_slot anchors ──


def test_battle_layout_has_hp_anchors():
    """battle_default should have player_hp_text and opponent_hp_bar."""
    anchors = DEFAULT_LAYOUTS.get('battle_default', {})
    assert 'player_hp_text' in anchors, 'Missing player_hp_text'
    assert 'opponent_hp_bar' in anchors, 'Missing opponent_hp_bar'


def test_battle_layout_has_move_slots():
    """battle_default should have 4 move_slot anchors."""
    anchors = DEFAULT_LAYOUTS.get('battle_default', {})
    for i in range(1, 5):
        key = f'move_slot_{i}'
        assert key in anchors, f'Missing anchor: {key}'


def test_build_roi_payloads_returns_battle_extras():
    """build_roi_payloads for battle should return HP + move slot payloads."""
    frame = {
        'width': 1920,
        'height': 1080,
        'layout_variant': 'battle_default',
        'preview_image_data_url': _make_preview_data_url(),
    }
    payloads = build_roi_payloads(frame, phase=BattlePhase.BATTLE, layout_variant='battle_default')

    assert 'player_hp_text' in payloads
    assert payloads['player_hp_text']['role'] == 'battle-player-hp-text'

    assert 'opponent_hp_bar' in payloads
    assert payloads['opponent_hp_bar']['role'] == 'battle-opponent-hp-bar'

    for i in range(1, 5):
        key = f'move_slot_{i}'
        assert key in payloads, f'Missing {key}'
        assert payloads[key]['role'] == f'battle-move-slot-{i}', f'Wrong role for {key}'


# ── Test 4: RecognitionStatePayload serializes new fields ──


def test_recognition_state_payload_team_slots_serialization():
    """RecognitionStatePayload should serialize player_team_slots and opponent_team_slots."""
    payload = RecognitionStatePayload(
        current_phase=BattlePhase.TEAM_SELECT,
        timestamp='2026-04-30T12:00:00Z',
        player_team_slots=[
            RecognizedTeamSlot(name='喷火龙', item='木炭', gender='male'),
            RecognizedTeamSlot(name='水箭龟', item=None, gender=None),
            RecognizedTeamSlot(name='妙蛙花', item='毒针', gender='female'),
        ] + [RecognizedTeamSlot() for _ in range(3)],
        opponent_team_slots=[
            RecognizedTeamSlot(sprite_match_id='pikachu', sprite_confidence=0.85),
        ] + [RecognizedTeamSlot() for _ in range(5)],
        locked_in=False,
    )

    data = payload.model_dump(mode='json')
    assert len(data['player_team_slots']) == 6
    assert data['player_team_slots'][0]['name'] == '喷火龙'
    assert data['player_team_slots'][0]['item'] == '木炭'
    assert data['player_team_slots'][0]['gender'] == 'male'
    assert data['opponent_team_slots'][0]['sprite_match_id'] == 'pikachu'
    assert data['opponent_team_slots'][0]['sprite_confidence'] == 0.85
    assert data['locked_in'] is False


def test_recognition_state_payload_hp_and_moves_serialization():
    """RecognitionStatePayload should serialize HP and revealed_moves fields."""
    payload = RecognitionStatePayload(
        current_phase=BattlePhase.BATTLE,
        timestamp='2026-04-30T12:00:00Z',
        player_hp_current=153,
        player_hp_max=204,
        opponent_hp_percent=67.5,
        revealed_moves=[
            {'name': '十万伏特', 'pp_current': 8, 'pp_max': 15, 'confidence': 0.9},
            {'name': '喷射火焰', 'pp_current': 5, 'pp_max': 10, 'confidence': 0.85},
        ],
    )

    data = payload.model_dump(mode='json')
    assert data['player_hp_current'] == 153
    assert data['player_hp_max'] == 204
    assert data['opponent_hp_percent'] == 67.5
    assert len(data['revealed_moves']) == 2
    assert data['revealed_moves'][0]['name'] == '十万伏特'
    assert data['revealed_moves'][0]['pp_current'] == 8


# ── Test 5: RecognizedTeamSlot model ──


def test_recognized_team_slot_defaults():
    """RecognizedTeamSlot should have sensible defaults."""
    slot = RecognizedTeamSlot()
    assert slot.name is None
    assert slot.item is None
    assert slot.gender is None
    assert slot.sprite_match_id is None
    assert slot.sprite_confidence == 0.0
    assert slot.is_selected is False


def test_recognized_team_slot_with_values():
    """RecognizedTeamSlot should store all fields."""
    slot = RecognizedTeamSlot(
        name='皮卡丘',
        item='电气球',
        gender='male',
        sprite_match_id='pikachu',
        sprite_confidence=0.95,
        is_selected=True,
    )
    assert slot.name == '皮卡丘'
    assert slot.item == '电气球'
    assert slot.gender == 'male'
    assert slot.sprite_match_id == 'pikachu'
    assert slot.sprite_confidence == 0.95
    assert slot.is_selected is True


# ── Test 6: BattleStateStore handles new team slots ──


class _SlotRecognizer:
    """Minimal recognizer stub that populates team slots."""

    def __init__(self):
        self._ocr_adapter = None
        self._matcher = None


def _make_team_select_payload(player_names=None, opponent_ids=None, locked_in=False):
    """Build a team_select RecognitionStatePayload with slot data."""
    player_slots = []
    for i in range(6):
        name = player_names[i] if player_names and i < len(player_names) else None
        player_slots.append(
            RecognizedTeamSlot(name=name, item=f'道具{i+1}', gender='male' if i % 2 == 0 else 'female')
        )

    opponent_slots = []
    for i in range(6):
        oid = opponent_ids[i] if opponent_ids and i < len(opponent_ids) else None
        opponent_slots.append(
            RecognizedTeamSlot(sprite_match_id=oid, sprite_confidence=0.8)
        )

    return RecognitionStatePayload(
        current_phase=BattlePhase.TEAM_SELECT,
        timestamp='2026-04-30T12:00:00Z',
        player_team_slots=player_slots,
        opponent_team_slots=opponent_slots,
        locked_in=locked_in,
        player=RecognizedSide(name='喷火龙', confidence=1.0, source=RecognitionSource.MOCK),
        opponent=RecognizedSide(name='皮卡丘', confidence=1.0, source=RecognitionSource.MOCK),
    )


def test_battle_state_store_team_slots():
    """BattleStateStore should build team roster from team slot data."""
    store = BattleStateStore()
    # Simulate battle start
    payload = _make_team_select_payload(
        player_names=['喷火龙', '水箭龟', '妙蛙花', None, None, None],
        opponent_ids=['pikachu', 'charizard', None, None, None, None],
    )
    store.update_from_recognition(payload)

    assert len(store.state.player_team) == 6
    assert store.state.player_team[0].name == '喷火龙'
    assert store.state.player_team[0].item == '道具1'
    assert store.state.player_team[0].gender == 'male'
    assert store.state.player_team[1].name == '水箭龟'
    assert store.state.player_team[1].gender == 'female'


def test_battle_state_store_team_lock():
    """BattleStateStore should mark first 3 as active when locked_in."""
    store = BattleStateStore()

    # First pass without lock
    payload = _make_team_select_payload(
        player_names=['喷火龙', '水箭龟', '妙蛙花', '皮卡丘', '卡比兽', '快龙'],
        locked_in=False,
    )
    store.update_from_recognition(payload)

    # None should be active yet
    for entry in store.state.player_team:
        assert entry.is_active is False, f'{entry.name} should not be active before lock'

    # Second pass with lock
    payload2 = _make_team_select_payload(
        player_names=['喷火龙', '水箭龟', '妙蛙花', '皮卡丘', '卡比兽', '快龙'],
        locked_in=True,
    )
    store.update_from_recognition(payload2)

    for i, entry in enumerate(store.state.player_team):
        if i < 3:
            assert entry.is_active is True, f'{entry.name} should be active after lock (slot {i})'
        else:
            assert entry.is_active is False, f'{entry.name} should not be active (slot {i})'


# ── Test 7: BattleStateStore handles HP data ──


def test_battle_state_store_hp_from_payload():
    """BattleStateStore should update HP from new payload fields."""
    store = BattleStateStore()
    store.reset()

    # Simulate battle recognition with HP data
    payload = RecognitionStatePayload(
        current_phase=BattlePhase.BATTLE,
        timestamp='2026-04-30T12:00:00Z',
        player=RecognizedSide(name='喷火龙', confidence=1.0, source=RecognitionSource.MOCK),
        opponent=RecognizedSide(name='皮卡丘', confidence=1.0, source=RecognitionSource.MOCK),
        player_hp_current=153,
        player_hp_max=204,
        opponent_hp_percent=67.5,
    )
    store.update_from_recognition(payload)

    # Player HP should be 75% (153/204)
    assert store.state.player_active.current_hp_percent is not None
    assert abs(store.state.player_active.current_hp_percent - 75.0) < 1.0

    # Opponent HP should be 67.5%
    assert store.state.opponent_active.current_hp_percent is not None
    assert abs(store.state.opponent_active.current_hp_percent - 67.5) < 0.1


# ── Test 8: BattleStateStore revealed moves ──


def test_battle_state_store_revealed_moves():
    """BattleStateStore should record revealed moves from payload."""
    store = BattleStateStore()
    store.reset()

    payload = RecognitionStatePayload(
        current_phase=BattlePhase.BATTLE,
        timestamp='2026-04-30T12:00:00Z',
        player=RecognizedSide(name='喷火龙', confidence=1.0, source=RecognitionSource.MOCK),
        opponent=RecognizedSide(name='皮卡丘', confidence=1.0, source=RecognitionSource.MOCK),
        revealed_moves=[
            {'name': '喷射火焰', 'pp_current': 5, 'pp_max': 10},
            {'name': '翅膀攻击', 'pp_current': 15, 'pp_max': 25},
        ],
    )
    store.update_from_recognition(payload)

    assert '喷射火焰' in store.state.player_active.revealed_moves
    assert '翅膀攻击' in store.state.player_active.revealed_moves
