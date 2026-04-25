import json
from pathlib import Path

from app.services.layout_anchors import get_layout_anchors
from app.services.roi_capture import build_pixel_box

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


def test_battle_move_menu_uses_user_confirmed_fixed_640x480_rois():
    sample = _load_sample('battle_move_menu_user_roi_gallade_frame_640x480.json')
    sample.pop('roi_candidates', None)

    anchors = get_layout_anchors(sample)

    frame = {'width': 640, 'height': 480}

    assert build_pixel_box(frame, anchors['player_status_panel']) == {
        'left': 10,
        'top': 385,
        'width': 210,
        'height': 90,
    }
    assert build_pixel_box(frame, anchors['opponent_status_panel']) == {
        'left': 455,
        'top': 15,
        'width': 180,
        'height': 90,
    }
    assert build_pixel_box(frame, anchors['move_list']) == {
        'left': 445,
        'top': 200,
        'width': 190,
        'height': 265,
    }


def test_get_layout_anchors_supports_team_select_layout():
    sample = _load_sample('team_select_hippowdon_preview.json')

    anchors = get_layout_anchors(sample)

    assert 'instruction_banner' in anchors
    assert 'player_team_list' in anchors
    assert anchors['selected_counter']['w'] == 0.16
