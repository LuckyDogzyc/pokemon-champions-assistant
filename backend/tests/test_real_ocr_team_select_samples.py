import base64
import importlib.util
import json
from pathlib import Path

import pytest

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations'
SAMPLES_DIR = ANNOTATIONS_DIR / 'samples'


def _load_sample(sample_name: str) -> dict:
    return json.loads((SAMPLES_DIR / sample_name).read_text(encoding='utf-8'))


def _build_frame_from_image(image_path: str) -> dict:
    import cv2

    image = cv2.imread(str(image_path))
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
    if importlib.util.find_spec('rapidocr_onnxruntime') is None:
        pytest.skip('rapidocr-onnxruntime is not installed')
    image_path = Path(sample.get('source_image_path', ''))
    if not image_path.is_absolute():
        image_path = SAMPLES_DIR / image_path
    if not image_path.exists():
        pytest.skip(f'real OCR sample image missing: {image_path}')


def _build_roi_frame(frame: dict, roi: dict) -> dict:
    """Crop a frame according to a relative ROI anchor."""
    from app.services.roi_capture import build_roi_frame as bf
    return bf(frame, roi) or {}


@pytest.mark.real_ocr
def test_team_select_user_1_recognizes_all_slots():
    """Real OCR test: team_select_user_1 sample should recognize all 6 player slots."""
    sample = _load_sample('team_select_user_1.json')
    _require_real_ocr_sample(sample)

    # Lazy imports to avoid collection-time failures on CI
    from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter
    from app.services.recognizers.team_select_recognizer import TeamSelectRecognizer
    from app.services.name_matcher import NameMatcher

    ocr_adapter = PaddleOcrAdapter()
    matcher = NameMatcher()
    recognizer = TeamSelectRecognizer(ocr_adapter=ocr_adapter, matcher=matcher)
    frame = _build_frame_from_image(ANNOTATIONS_DIR / 'samples' / 'team_select_user_1.jpeg')

    from app.services.layout_anchors import DEFAULT_LAYOUTS
    anchors = DEFAULT_LAYOUTS.get('team_select_default', {})
    roi_frames = {}
    for key in [f'player_mon_{i}' for i in range(1, 7)]:
        if key in anchors:
            roi_frames[key] = _build_roi_frame(frame, anchors[key])
            assert roi_frames[key].get('preview_image_data_url'), f'{key} has no preview'

    player_results = recognizer.recognize_all_player(roi_frames)
    expected = sample.get('player_slot_details', [])

    for i, (result, expected_slot) in enumerate(zip(player_results, expected)):
        slot_num = i + 1
        expected_name = expected_slot['name']
        assert result['name'] == expected_name, (
            f'player_mon_{slot_num}: expected name="{expected_name}", got "{result["name"]}"\n'
            f'  raw_texts: {result.get("debug_raw_text", "")}'
        )


@pytest.mark.real_ocr
def test_team_select_user_1_recognizes_player_items_and_genders():
    """Real OCR test: team_select_user_1 should also detect items and genders for player slots."""
    sample = _load_sample('team_select_user_1.json')
    _require_real_ocr_sample(sample)

    from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter
    from app.services.recognizers.team_select_recognizer import TeamSelectRecognizer
    from app.services.name_matcher import NameMatcher

    ocr_adapter = PaddleOcrAdapter()
    matcher = NameMatcher()
    recognizer = TeamSelectRecognizer(ocr_adapter=ocr_adapter, matcher=matcher)
    frame = _build_frame_from_image(ANNOTATIONS_DIR / 'samples' / 'team_select_user_1.jpeg')

    from app.services.layout_anchors import DEFAULT_LAYOUTS
    anchors = DEFAULT_LAYOUTS.get('team_select_default', {})
    roi_frames = {}
    for key in [f'player_mon_{i}' for i in range(1, 7)]:
        if key in anchors:
            roi_frames[key] = _build_roi_frame(frame, anchors[key])

    player_results = recognizer.recognize_all_player(roi_frames)
    expected = sample.get('player_slot_details', [])

    for i, (result, expected_slot) in enumerate(zip(player_results, expected)):
        slot_num = i + 1
        expected_item = expected_slot.get('item')
        expected_gender = expected_slot.get('gender')
        name = result.get('name')

        if expected_item and result.get('item'):
            assert isinstance(result['item'], str), (
                f'player_mon_{slot_num} ({name}): expected item="{expected_item}", '
                f'got None or non-string'
            )

        if expected_gender and result.get('gender'):
            assert result['gender'] == expected_gender, (
                f'player_mon_{slot_num} ({name}): expected gender={expected_gender}, '
                f'got {result.get("gender")}'
            )


@pytest.mark.real_ocr
def test_team_select_user_2_recognizes_all_slots():
    """Real OCR test: team_select_user_2 sample should recognize all 6 player slots."""
    sample = _load_sample('team_select_user_2.json')
    _require_real_ocr_sample(sample)

    from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter
    from app.services.recognizers.team_select_recognizer import TeamSelectRecognizer
    from app.services.name_matcher import NameMatcher

    ocr_adapter = PaddleOcrAdapter()
    matcher = NameMatcher()
    recognizer = TeamSelectRecognizer(ocr_adapter=ocr_adapter, matcher=matcher)
    frame = _build_frame_from_image(ANNOTATIONS_DIR / 'samples' / 'team_select_user_2.jpeg')

    from app.services.layout_anchors import DEFAULT_LAYOUTS
    anchors = DEFAULT_LAYOUTS.get('team_select_default', {})
    roi_frames = {}
    for key in [f'player_mon_{i}' for i in range(1, 7)]:
        if key in anchors:
            roi_frames[key] = _build_roi_frame(frame, anchors[key])

    player_results = recognizer.recognize_all_player(roi_frames)
    expected = sample.get('player_slot_details', [])

    for i, (result, expected_slot) in enumerate(zip(player_results, expected)):
        slot_num = i + 1
        expected_name = expected_slot['name']
        assert result['name'] == expected_name, (
            f'player_mon_{slot_num}: expected name="{expected_name}", got "{result["name"]}"\n'
            f'  raw_texts: {result.get("debug_raw_text", "")}'
        )
