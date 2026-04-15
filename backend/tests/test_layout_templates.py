import json
from pathlib import Path

from app.services.layout_anchors import get_layout_anchors

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations' / 'samples'


def _load_sample(name: str) -> dict:
    return json.loads((ANNOTATIONS_DIR / name).read_text(encoding='utf-8'))


def test_get_layout_anchors_returns_named_rois_for_battle_default():
    sample = _load_sample('battle_default_garchomp_vs_froslass.json')

    anchors = get_layout_anchors(sample)

    assert anchors['player_name']['x'] == 0.03
    assert anchors['opponent_name']['y'] == 0.06
    assert 'command_panel' in anchors


def test_get_layout_anchors_supports_team_select_layout():
    sample = _load_sample('team_select_hippowdon_preview.json')

    anchors = get_layout_anchors(sample)

    assert 'instruction_banner' in anchors
    assert 'player_team_list' in anchors
    assert anchors['selected_counter']['w'] == 0.16
