import json
from pathlib import Path

from app.services.phase_detector import PhaseDetector

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations' / 'samples'


def _load_sample(name: str) -> dict:
    return json.loads((ANNOTATIONS_DIR / name).read_text(encoding='utf-8'))


def _build_frame_from_annotation(sample: dict) -> dict:
    return {
        'width': sample['image']['width'],
        'height': sample['image']['height'],
        'ocr_texts': sample['anchors']['required_texts'] + sample['anchors'].get('optional_texts', []),
        'layout_variant_hint': sample['layout_variant'],
    }


def test_phase_detector_recognizes_battle_from_real_annotation_texts():
    sample = _load_sample('battle_default_garchomp_vs_froslass.json')
    detector = PhaseDetector()

    result = detector.detect(_build_frame_from_annotation(sample))

    assert result.phase == 'battle'
    assert result.confidence >= 0.8
    assert 'COMMAND' in ' '.join(result.evidence)


def test_phase_detector_recognizes_team_select_from_real_annotation_texts():
    sample = _load_sample('team_select_hippowdon_preview.json')
    detector = PhaseDetector()

    result = detector.detect(_build_frame_from_annotation(sample))

    assert result.phase == 'team_select'
    assert result.confidence >= 0.8
    assert any('选择完毕' in item or '3只要上场战斗' in item for item in result.evidence)
