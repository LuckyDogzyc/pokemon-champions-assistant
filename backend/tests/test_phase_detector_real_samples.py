import json
from pathlib import Path

import pytest

from app.services.phase_detector import PhaseDetector

ANNOTATIONS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'annotations'
SAMPLES_DIR = ANNOTATIONS_DIR / 'samples'
SAMPLES_INDEX = SAMPLES_DIR / 'index.json'


def _load_sample_index() -> list[dict]:
    return json.loads(SAMPLES_INDEX.read_text(encoding='utf-8'))


def _load_sample_by_index_entry(entry: dict) -> dict:
    return json.loads((ANNOTATIONS_DIR / entry['path']).read_text(encoding='utf-8'))


def _build_frame_from_annotation(sample: dict) -> dict:
    return {
        'width': sample['image']['width'],
        'height': sample['image']['height'],
        'ocr_texts': sample['anchors']['required_texts'] + sample['anchors'].get('optional_texts', []),
        'layout_variant_hint': sample['layout_variant'],
    }


@pytest.mark.parametrize('entry', _load_sample_index(), ids=lambda entry: entry['sample_id'])
def test_phase_detector_matches_expected_phase_for_indexed_real_samples(entry: dict):
    sample = _load_sample_by_index_entry(entry)
    detector = PhaseDetector()

    result = detector.detect(_build_frame_from_annotation(sample))

    assert result.phase == sample['phase']['expected_phase'] == entry['phase']
    assert result.confidence >= 0.8
    assert result.evidence


@pytest.mark.parametrize('entry', _load_sample_index(), ids=lambda entry: entry['sample_id'])
def test_phase_detector_sample_index_points_to_existing_json_fixture(entry: dict):
    sample_path = ANNOTATIONS_DIR / entry['path']
    assert sample_path.exists(), f'missing sample fixture: {sample_path}'
    sample = json.loads(sample_path.read_text(encoding='utf-8'))
    assert sample['sample_id'] == entry['sample_id']
    assert sample['layout_variant'] == entry['layout_variant']
