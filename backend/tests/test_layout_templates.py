import json
from pathlib import Path

from app.services.layout_anchors import get_layout_anchors

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations' / 'samples'


def _load_sample(name: str) -> dict:
    return json.loads((ANNOTATIONS_DIR / name).read_text(encoding='utf-8'))


def test_get_layout_anchors_returns_battle_status_rois_for_battle_default():
    sample = _load_sample('battle_default_user_roi_garchomp_frame_640x480.json')

    anchors = get_layout_anchors(sample)

    assert 'player_status_panel' in anchors
    assert 'opponent_status_panel' in anchors
    assert 'command_panel' not in anchors
    assert 'player_name' not in anchors
    assert 'opponent_name' not in anchors


def test_get_layout_anchors_returns_move_list_without_command_panel_for_battle_move_menu_open():
    sample = _load_sample('battle_move_menu_user_roi_gallade_frame_640x480.json')

    anchors = get_layout_anchors(sample)

    assert 'move_list' in anchors
    assert 'player_status_panel' in anchors
    assert 'opponent_status_panel' in anchors
    assert 'command_panel' not in anchors
    assert 'player_name' not in anchors
    assert 'opponent_name' not in anchors


def test_get_layout_anchors_supports_team_select_layout():
    sample = _load_sample('team_select_hippowdon_preview.json')

    anchors = get_layout_anchors(sample)

    assert 'instruction_banner' in anchors
    assert 'player_team_list' in anchors
    assert anchors['selected_counter']['w'] == 0.16
