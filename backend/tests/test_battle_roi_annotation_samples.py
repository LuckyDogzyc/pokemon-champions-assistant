import json
from pathlib import Path

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations'
SAMPLES_DIR = ANNOTATIONS_DIR / 'samples'


def _load_sample(sample_name: str) -> dict:
    return json.loads((SAMPLES_DIR / sample_name).read_text(encoding='utf-8'))


def test_battle_default_user_sample_only_keeps_status_panel_roi_candidates():
    sample = _load_sample('battle_default_user_roi_garchomp_frame_640x480.json')

    assert sample['phase']['battle_substate'] == 'battle_default'
    assert set(sample['roi_expectations']) == {'player_status_panel', 'opponent_status_panel'}
    assert set(sample['roi_candidates']) == {'player_status_panel', 'opponent_status_panel'}
    assert 'command_panel' not in sample['notes']


def test_battle_move_menu_user_sample_locks_four_moves_with_minimal_battle_rois():
    sample = _load_sample('battle_move_menu_user_roi_gallade_frame_640x480.json')

    assert sample['phase']['battle_substate'] == 'battle_move_menu_open'
    assert set(sample['roi_candidates']) == {'player_status_panel', 'opponent_status_panel', 'move_list'}

    move_list_roi = sample['roi_candidates']['move_list']
    move_list = sample['roi_expectations']['move_list']
    expected_moves = {'千变万花', '拍落', '急速折返', '三旋击'}

    assert move_list_roi['x'] == 0.695312
    assert move_list_roi['y'] == 0.416667
    assert move_list_roi['w'] == 0.296875
    assert move_list_roi['h'] == 0.552083
    assert move_list_roi['confidence'] == 'fixed'
    assert move_list['strong']['move_order_sensitive'] is False
    assert set(move_list['strong']['move_names']) == expected_moves
    assert len(move_list['strong']['move_names']) == 4
    assert move_list['strong']['pp_texts'] == ['12/12', '20/20', '20/20', '12/12']
    assert 'possible_move_names' not in move_list.get('weak', {})
    assert '顺序暂时没关系' in move_list['notes']
    assert '不是顶部没截到' in move_list['notes']
