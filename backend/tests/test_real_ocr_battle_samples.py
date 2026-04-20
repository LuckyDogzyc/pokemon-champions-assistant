import base64
import importlib.util
import json
from pathlib import Path

import cv2
import pytest

from app.services.recognizers.chinese_ocr_recognizer import ChineseOcrSideRecognizer
from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations'
SAMPLES_DIR = ANNOTATIONS_DIR / 'samples'


def _load_sample(sample_name: str) -> dict:
    return json.loads((SAMPLES_DIR / sample_name).read_text(encoding='utf-8'))


def _build_frame_from_image(image_path: str) -> dict:
    image = cv2.imread(image_path)
    assert image is not None, f'failed to read sample image: {image_path}'
    height, width = image.shape[:2]
    ok, encoded = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    assert ok, f'failed to encode sample image: {image_path}'
    return {
        'width': width,
        'height': height,
        'preview_image_data_url': 'data:image/jpeg;base64,' + base64.b64encode(encoded.tobytes()).decode('ascii'),
    }


def _require_real_ocr_sample(sample: dict) -> None:
    if importlib.util.find_spec('paddleocr') is None:
        pytest.skip('paddleocr is not installed')
    image_path = Path(sample['source_image_path'])
    if not image_path.exists():
        pytest.skip(f'real OCR sample image missing: {image_path}')


@pytest.mark.real_ocr
def test_real_ocr_battle_move_menu_user_sample_recognizes_key_status_and_moves():
    sample = _load_sample('battle_move_menu_user_roi_gallade_frame_640x480.json')
    _require_real_ocr_sample(sample)

    recognizer = ChineseOcrSideRecognizer(ocr_adapter=PaddleOcrAdapter())
    frame = _build_frame_from_image(sample['source_image_path'])
    rois = sample['roi_candidates']

    player = recognizer.recognize_named_roi(frame, rois['player_status_panel'], 'player_status_panel')
    opponent = recognizer.recognize_named_roi(frame, rois['opponent_status_panel'], 'opponent_status_panel')
    move_list = recognizer.recognize_named_roi(frame, rois['move_list'], 'move_list')

    assert player['pokemon_name'] == '魔幻假面喵'
    assert player['hp_text'] == '183/183'
    assert opponent['pokemon_name'] == '烈咬陆鲨'

    recognized_moves = set(move_list['recognized_texts'])
    expected_moves = {'千变万花', '拍落', '急速折返', '三旋击'}

    assert move_list['recognized_count'] == 4
    assert recognized_moves == expected_moves
    assert 'COMMAND 37' not in recognized_moves
    assert '查看状态' not in recognized_moves
    assert '招式说明' not in recognized_moves
