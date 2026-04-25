import base64
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.services.recognition_pipeline import RecognitionPipeline
from app.services.recognizers.chinese_ocr_recognizer import ChineseOcrSideRecognizer


def _make_preview_data_url(width=200, height=100):
    header = f'P6\n{width} {height}\n255\n'.encode('ascii')
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels.extend(((x * 3) % 256, (y * 5) % 256, ((x + y) * 7) % 256))
    return 'data:image/x-portable-pixmap;base64,' + base64.b64encode(header + bytes(pixels)).decode('ascii')


class StubPhaseDetector:
    def detect(self, frame):
        from app.schemas.phase import PhaseDetectionResult

        return PhaseDetectionResult(
            phase='team_select',
            confidence=0.95,
            evidence=['请选择出3只要上场战斗的宝可梦。', '选择完毕'],
        )


class StubBattlePhaseDetector:
    def detect(self, frame):
        from app.schemas.phase import PhaseDetectionResult

        return PhaseDetectionResult(
            phase='battle',
            confidence=0.91,
            evidence=['COMMAND 43', '雪妖女'],
        )


class StubRecognizer:
    def __init__(self):
        self.named_roi_calls = []

    def recognize_side(self, frame, roi, side):
        if side == 'player':
            return {
                'name': '大竺葵',
                'confidence': 0.93,
                'source': 'ocr',
                'roi': roi,
                'raw_text': '大竺葵',
                'matched_by': 'exact',
            }
        return {
            'name': '雪妖女',
            'confidence': 0.84,
            'source': 'ocr',
            'roi': roi,
            'raw_text': '雪妖女',
            'matched_by': 'exact',
        }

    def recognize_named_roi(self, frame, roi, roi_name):
        self.named_roi_calls.append({'frame': frame, 'roi': roi, 'roi_name': roi_name})
        if roi_name == 'move_list':
            return {
                'recognized_texts': ['能量球', '守住', '觉醒力量'],
                'recognized_count': 3,
            }
        if roi_name in ('player_status_panel', 'opponent_status_panel'):
            return {
                'pokemon_name': '大竺葵' if roi_name == 'player_status_panel' else '雪妖女',
                'hp_text': '120/150',
                'hp_percentage': '80%',
                'matched_by': 'ocr-status-panel',
                'raw_texts': ['大竺葵', 'HP 120/150', '80%'],
                'raw_count': 3,
            }
        return None


class StubMoveListOcrAdapter:
    def read_text(self, frame, roi):
        if frame.get('width') == 44 and frame.get('height') == 36:
            return [
                {'text': 'COMMAND 43', 'score': 0.99},
                {'text': '招式说明', 'score': 0.98},
                {'text': '日光束', 'score': 0.95},
                {'text': '魔法闪耀', 'score': 0.94},
                {'text': '光合作用', 'score': 0.93},
                {'text': '气象球', 'score': 0.92},
            ]
        if roi in (
            {'x': 0.03, 'y': 0.83, 'w': 0.18, 'h': 0.06, 'confidence': 'approx'},
            {'x': 0.08, 'y': 0.80, 'w': 0.22, 'h': 0.07, 'confidence': 'approx'},
        ):
            return [{'text': '大竺葵', 'score': 0.95}]
        return [{'text': '雪妖女', 'score': 0.91}]


def test_recognition_pipeline_returns_team_preview_state_for_team_select():
    pipeline = RecognitionPipeline(phase_detector=StubPhaseDetector(), recognizer=StubRecognizer())

    result = pipeline.recognize(
        {
            'timestamp': '2026-04-15T16:00:00Z',
            'layout_variant_hint': 'team_select_default',
            'annotation_target': {
                'player_team': ['河马兽', '烈咬陆鲨', '幽尾玄鱼', '大竺葵', '铝钢桥龙', '海豚侠'],
                'opponent_team': ['火神蛾', '西狮海壬', '烈咬陆鲨'],
                'selected_count': 0,
                'instruction_text': '请选择出3只要上场战斗的宝可梦。',
            },
        }
    )

    assert result.current_phase == 'team_select'
    assert result.layout_variant == 'team_select_default'
    assert result.team_preview is not None
    assert result.team_preview.selected_count == 0
    assert result.team_preview.player_team[0] == '河马兽'
    assert '选择完毕' in result.phase_evidence
    assert result.phase_snapshot == {
        'phase': 'team_select',
        'confidence': 0.95,
        'evidence': ['请选择出3只要上场战斗的宝可梦。', '选择完毕'],
    }
    assert result.roi_payloads['instruction_banner']['role'] == 'phase-detection'
    assert result.roi_payloads['player_team_list']['source'] == 'roi-source-frame'


def test_recognition_pipeline_returns_debug_fields_for_battle_recognition():
    pipeline = RecognitionPipeline(phase_detector=StubBattlePhaseDetector(), recognizer=StubRecognizer())

    result = pipeline.recognize(
        {
            'width': 1920,
            'height': 1080,
            'timestamp': '2026-04-15T16:01:00Z',
            'layout_variant_hint': 'battle_move_menu_open',
        }
    )

    assert result.current_phase == 'battle'
    assert result.layout_variant == 'battle_move_menu_open'
    assert result.player.debug_raw_text == '大竺葵'
    assert result.opponent.debug_raw_text == '雪妖女'
    assert result.player.debug_roi is not None
    assert 'COMMAND 43' in result.phase_evidence
    assert result.phase_snapshot == {
        'phase': 'battle',
        'confidence': 0.91,
        'evidence': ['COMMAND 43', '雪妖女'],
    }
    assert 'player_name' not in result.roi_payloads
    assert 'opponent_name' not in result.roi_payloads
    assert 'command_panel' not in result.roi_payloads
    assert result.roi_payloads['player_status_panel']['role'] == 'battle-player-status-panel'
    assert result.roi_payloads['move_list']['role'] == 'battle-move-list'


class OverlapDetectingBattlePhaseDetector:
    def __init__(self):
        self._lock = threading.Lock()
        self.concurrent_calls = 0
        self._active_calls = 0

    def detect(self, frame):
        with self._lock:
            self._active_calls += 1
            if self._active_calls > 1:
                self.concurrent_calls += 1
        time.sleep(0.05)
        try:
            from app.schemas.phase import PhaseDetectionResult

            return PhaseDetectionResult(
                phase='battle',
                confidence=0.91,
                evidence=['COMMAND 43', '雪妖女'],
            )
        finally:
            with self._lock:
                self._active_calls -= 1


class PassiveBattleRecognizer:
    def recognize_side(self, frame, roi, side):
        return {
            'name': '大竺葵' if side == 'player' else '雪妖女',
            'confidence': 0.9,
            'source': 'ocr',
            'roi': roi,
            'raw_text': '大竺葵' if side == 'player' else '雪妖女',
            'matched_by': 'exact',
        }


def test_recognition_pipeline_serializes_concurrent_recognize_calls():
    detector = OverlapDetectingBattlePhaseDetector()
    pipeline = RecognitionPipeline(phase_detector=detector, recognizer=PassiveBattleRecognizer())
    frame = {
        'width': 1920,
        'height': 1080,
        'timestamp': '2026-04-15T16:01:00Z',
        'layout_variant_hint': 'battle_move_menu_open',
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(pipeline.recognize, dict(frame)) for _ in range(2)]
        results = [future.result() for future in futures]

    assert detector.concurrent_calls == 0
    assert [result.current_phase for result in results] == ['battle', 'battle']


def test_recognition_pipeline_exposes_default_battle_auxiliary_rois_without_annotations():
    pipeline = RecognitionPipeline(phase_detector=StubBattlePhaseDetector(), recognizer=StubRecognizer())

    result = pipeline.recognize(
        {
            'width': 1920,
            'height': 1080,
            'timestamp': '2026-04-15T16:01:30Z',
            'layout_variant_hint': 'battle_move_menu_open',
            'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
        }
    )

    assert result.roi_payloads['player_status_panel']['role'] == 'battle-player-status-panel'
    assert result.roi_payloads['opponent_status_panel']['role'] == 'battle-opponent-status-panel'
    assert 'command_panel' not in result.roi_payloads
    assert result.roi_payloads['move_list']['role'] == 'battle-move-list'


def test_recognition_pipeline_builds_real_battle_roi_crops_and_named_roi_results():
    recognizer = StubRecognizer()
    pipeline = RecognitionPipeline(phase_detector=StubBattlePhaseDetector(), recognizer=recognizer)

    result = pipeline.recognize(
        {
            'width': 200,
            'height': 100,
            'timestamp': '2026-04-15T16:02:00Z',
            'layout_variant_hint': 'battle_move_menu_open',
            'preview_image_data_url': _make_preview_data_url(),
            'roi_candidates': {
                'player_name': {'x': 0.05, 'y': 0.78, 'w': 0.25, 'h': 0.1, 'confidence': 'approx'},
                'opponent_name': {'x': 0.68, 'y': 0.05, 'w': 0.2, 'h': 0.08, 'confidence': 'approx'},
                'player_status_panel': {'x': 0.02, 'y': 0.74, 'w': 0.35, 'h': 0.2, 'confidence': 'approx'},
                'opponent_status_panel': {'x': 0.60, 'y': 0.02, 'w': 0.32, 'h': 0.18, 'confidence': 'approx'},
                'move_list': {'x': 0.70, 'y': 0.42, 'w': 0.24, 'h': 0.32, 'confidence': 'approx'},
            },
        }
    )

    assert result.roi_payloads['player_status_panel']['pixel_box'] == {
        'left': 4,
        'top': 74,
        'width': 70,
        'height': 20,
    }
    assert result.roi_payloads['player_status_panel']['preview_image_data_url'].startswith('data:image/jpeg;base64,')
    assert result.roi_payloads['opponent_status_panel']['pixel_box'] == {
        'left': 120,
        'top': 2,
        'width': 64,
        'height': 18,
    }
    assert result.roi_payloads['move_list']['recognized_texts'] == ['能量球', '守住', '觉醒力量']
    assert result.roi_payloads['move_list']['recognized_count'] == 3
    # Named ROI calls are in payload creation order: player_status_panel, opponent_status_panel, move_list
    roi_names_in_order = [call['roi_name'] for call in recognizer.named_roi_calls]
    assert 'player_status_panel' in roi_names_in_order
    assert 'opponent_status_panel' in roi_names_in_order
    assert 'move_list' in roi_names_in_order
    # Find move_list call and verify it
    move_list_call = next(call for call in recognizer.named_roi_calls if call['roi_name'] == 'move_list')
    assert move_list_call['frame']['width'] == 48
    assert move_list_call['frame']['height'] == 32
    assert move_list_call['frame']['preview_image_data_url'].startswith('data:image/jpeg;base64,')


def test_recognition_pipeline_uses_chinese_ocr_recognizer_for_move_list_named_roi():
    recognizer = ChineseOcrSideRecognizer(ocr_adapter=StubMoveListOcrAdapter())
    pipeline = RecognitionPipeline(phase_detector=StubBattlePhaseDetector(), recognizer=recognizer)

    result = pipeline.recognize(
        {
            'width': 200,
            'height': 100,
            'timestamp': '2026-04-15T16:03:00Z',
            'layout_variant_hint': 'battle_move_menu_open',
            'preview_image_data_url': _make_preview_data_url(),
            'roi_candidates': {
                'player_name': {'x': 0.03, 'y': 0.83, 'w': 0.18, 'h': 0.06, 'confidence': 'approx'},
                'opponent_name': {'x': 0.73, 'y': 0.05, 'w': 0.18, 'h': 0.06, 'confidence': 'approx'},
                'move_list': {'x': 0.72, 'y': 0.40, 'w': 0.22, 'h': 0.36, 'confidence': 'approx'},
            },
        }
    )

    assert result.player.name == '大竺葵'
    assert result.opponent.name == '雪妖女'
    assert result.roi_payloads['move_list']['recognized_texts'] == ['日光束', '魔法闪耀', '光合作用', '气象球']
    assert result.roi_payloads['move_list']['recognized_count'] == 4
    assert result.roi_payloads['move_list']['matched_by'] == 'ocr-text-list'


class StubStatusPanelOcrAdapter:
    _player_status_texts = [
        {'text': '大竺葵', 'score': 0.96},
        {'text': 'HP 120/150', 'score': 0.94},
        {'text': '80%', 'score': 0.91},
        {'text': '中毒', 'score': 0.88},
    ]
    _opponent_status_texts = [
        {'text': '雪妖女', 'score': 0.93},
        {'text': 'HP 80/80', 'score': 0.91},
        {'text': 'Lv.50', 'score': 0.90},
    ]

    def read_text(self, frame, roi):
        # When OCR reads the status panel ROI, return corresponding texts
        w = float(roi.get('w', 0))
        x = float(roi.get('x', 0))
        # player_status_panel is on the left (x ≈ 0.02)
        # opponent_status_panel is on the right (x ≈ 0.60 or 0.69)
        if x < 0.3:
            return self._player_status_texts
        return self._opponent_status_texts


def test_recognition_pipeline_calls_status_panel_ocr_and_enriches_roi_payloads():
    recognizer = ChineseOcrSideRecognizer(ocr_adapter=StubStatusPanelOcrAdapter())
    pipeline = RecognitionPipeline(phase_detector=StubBattlePhaseDetector(), recognizer=recognizer)

    result = pipeline.recognize(
        {
            'width': 1920,
            'height': 1080,
            'timestamp': '2026-04-15T16:04:00Z',
            'layout_variant_hint': 'battle_default',
            'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
            'roi_candidates': {
                'player_name': {'x': 0.08, 'y': 0.80, 'w': 0.22, 'h': 0.07, 'confidence': 'approx'},
                'opponent_name': {'x': 0.70, 'y': 0.10, 'w': 0.22, 'h': 0.07, 'confidence': 'approx'},
                'player_status_panel': {'x': 0.02, 'y': 0.78, 'w': 0.25, 'h': 0.14, 'confidence': 'approx'},
                'opponent_status_panel': {'x': 0.69, 'y': 0.03, 'w': 0.28, 'h': 0.13, 'confidence': 'approx'},
            },
        }
    )

    assert result.roi_payloads['player_status_panel']['pokemon_name'] == '大竺葵'
    assert result.roi_payloads['player_status_panel']['hp_text'] == '120/150'
    assert result.roi_payloads['player_status_panel']['hp_percentage'] == '80%'
    assert result.roi_payloads['player_status_panel']['status_abnormality'] == '中毒'
    assert result.roi_payloads['player_status_panel']['matched_by'] == 'ocr-status-panel'

    assert result.roi_payloads['opponent_status_panel']['pokemon_name'] == '雪妖女'
    assert result.roi_payloads['opponent_status_panel']['hp_text'] == '80/80'
    assert result.roi_payloads['opponent_status_panel']['level'] == 'Lv.50'
    assert result.roi_payloads['opponent_status_panel']['matched_by'] == 'ocr-status-panel'


def test_recognition_pipeline_passes_status_panel_roi_frame_to_ocr():
    recognizer = StubRecognizer()
    pipeline = RecognitionPipeline(phase_detector=StubBattlePhaseDetector(), recognizer=recognizer)

    result = pipeline.recognize(
        {
            'width': 1920,
            'height': 1080,
            'timestamp': '2026-04-15T16:05:00Z',
            'layout_variant_hint': 'battle_default',
            'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
            'roi_candidates': {
                'player_name': {'x': 0.08, 'y': 0.80, 'w': 0.22, 'h': 0.07, 'confidence': 'approx'},
                'opponent_name': {'x': 0.70, 'y': 0.10, 'w': 0.22, 'h': 0.07, 'confidence': 'approx'},
                'player_status_panel': {'x': 0.02, 'y': 0.78, 'w': 0.25, 'h': 0.14, 'confidence': 'approx'},
                'opponent_status_panel': {'x': 0.69, 'y': 0.03, 'w': 0.28, 'h': 0.13, 'confidence': 'approx'},
                'move_list': {'x': 0.73, 'y': 0.43, 'w': 0.23, 'h': 0.36, 'confidence': 'approx'},
            },
        }
    )

    # Should have called recognize_named_roi for all 3 named ROIs
    roi_names_called = [call['roi_name'] for call in recognizer.named_roi_calls]
    assert 'player_status_panel' in roi_names_called
    assert 'opponent_status_panel' in roi_names_called
    assert 'move_list' in roi_names_called

    # Verify status panel ROI calls had valid frame with preview
    for call in recognizer.named_roi_calls:
        if call['roi_name'] in ('player_status_panel', 'opponent_status_panel'):
            assert call['frame']['preview_image_data_url'].startswith('data:image/jpeg;base64,')


class RecordingFrameVariantsPhaseDetector:
    def __init__(self):
        self.frames = []

    def detect(self, frame):
        from app.schemas.phase import PhaseDetectionResult

        self.frames.append(frame)
        return PhaseDetectionResult(
            phase='battle',
            confidence=0.92,
            evidence=['COMMAND 43'],
        )


class RecordingFrameVariantsRecognizer(StubRecognizer):
    def __init__(self):
        super().__init__()
        self.side_calls = []

    def recognize_side(self, frame, roi, side):
        self.side_calls.append({'frame': frame, 'roi': roi, 'side': side})
        return super().recognize_side(frame, roi, side)


def test_recognition_pipeline_routes_phase_detector_to_phase_frame_variant():
    phase_detector = RecordingFrameVariantsPhaseDetector()
    pipeline = RecognitionPipeline(phase_detector=phase_detector, recognizer=StubRecognizer())
    phase_preview = _make_preview_data_url(width=40, height=20)
    roi_preview = _make_preview_data_url(width=200, height=100)
    outer_preview = _make_preview_data_url(width=50, height=25)

    result = pipeline.recognize(
        {
            'width': 50,
            'height': 25,
            'timestamp': '2026-04-19T13:35:00Z',
            'layout_variant_hint': 'battle_move_menu_open',
            'preview_image_data_url': outer_preview,
            'frame_variants': {
                'phase_frame': {
                    'width': 40,
                    'height': 20,
                    'preview_image_data_url': phase_preview,
                    'ocr_texts': ['COMMAND 43', '招式说明'],
                    'layout_variant_hint': 'battle_move_menu_open',
                },
                'roi_source_frame': {
                    'width': 200,
                    'height': 100,
                    'preview_image_data_url': roi_preview,
                    'layout_variant_hint': 'battle_move_menu_open',
                },
            },
        }
    )

    assert result.current_phase == 'battle'
    assert phase_detector.frames[0]['preview_image_data_url'] == phase_preview
    assert phase_detector.frames[0]['width'] == 40
    assert phase_detector.frames[0]['height'] == 20
    assert phase_detector.frames[0]['ocr_texts'] == ['COMMAND 43', '招式说明']


def test_recognition_pipeline_routes_battle_roi_and_side_recognition_to_roi_source_frame_variant():
    phase_detector = RecordingFrameVariantsPhaseDetector()
    recognizer = RecordingFrameVariantsRecognizer()
    pipeline = RecognitionPipeline(phase_detector=phase_detector, recognizer=recognizer)
    phase_preview = _make_preview_data_url(width=40, height=20)
    roi_preview = _make_preview_data_url(width=200, height=100)
    outer_preview = _make_preview_data_url(width=50, height=25)

    result = pipeline.recognize(
        {
            'width': 50,
            'height': 25,
            'timestamp': '2026-04-19T13:36:00Z',
            'layout_variant_hint': 'battle_move_menu_open',
            'preview_image_data_url': outer_preview,
            'frame_variants': {
                'phase_frame': {
                    'width': 40,
                    'height': 20,
                    'preview_image_data_url': phase_preview,
                    'ocr_texts': ['COMMAND 43', '招式说明'],
                    'layout_variant_hint': 'battle_move_menu_open',
                },
                'roi_source_frame': {
                    'width': 200,
                    'height': 100,
                    'preview_image_data_url': roi_preview,
                    'layout_variant_hint': 'battle_move_menu_open',
                },
            },
            'roi_candidates': {
                'player_name': {'x': 0.05, 'y': 0.78, 'w': 0.25, 'h': 0.1, 'confidence': 'approx'},
                'opponent_name': {'x': 0.68, 'y': 0.05, 'w': 0.2, 'h': 0.08, 'confidence': 'approx'},
                'player_status_panel': {'x': 0.02, 'y': 0.74, 'w': 0.35, 'h': 0.2, 'confidence': 'approx'},
                'opponent_status_panel': {'x': 0.60, 'y': 0.02, 'w': 0.32, 'h': 0.18, 'confidence': 'approx'},
                'move_list': {'x': 0.70, 'y': 0.42, 'w': 0.24, 'h': 0.32, 'confidence': 'approx'},
            },
        }
    )

    assert result.player.name == '大竺葵'
    assert result.opponent.name == '雪妖女'
    assert recognizer.side_calls[0]['frame']['preview_image_data_url'] == roi_preview
    assert recognizer.side_calls[1]['frame']['preview_image_data_url'] == roi_preview
    move_list_call = next(call for call in recognizer.named_roi_calls if call['roi_name'] == 'move_list')
    assert move_list_call['frame']['source_preview_image_data_url'] == roi_preview
    assert move_list_call['frame']['width'] == 48
    assert move_list_call['frame']['height'] == 32
    assert result.roi_payloads['move_list']['pixel_box'] == {
        'left': 140,
        'top': 42,
        'width': 48,
        'height': 32,
    }


class PhaseFrameOcrAdapter:
    def __init__(self):
        self.calls = []

    def read_text(self, frame, roi):
        self.calls.append({'frame': frame, 'roi': roi})
        return [
            {'text': '请选择出3只要上场战斗的宝可梦。', 'score': 0.99},
            {'text': '选择完毕', 'score': 0.98},
            {'text': '0/3', 'score': 0.97},
        ]


class RecordingTeamSelectPhaseDetector:
    def __init__(self):
        self.detect_calls = []

    def detect(self, frame):
        from app.schemas.phase import PhaseDetectionResult

        self.detect_calls.append(frame)
        texts = frame.get('ocr_texts', [])
        if any('请选择出3只要上场战斗的宝可梦' in text for text in texts):
            return PhaseDetectionResult(
                phase='team_select',
                confidence=0.94,
                evidence=texts,
            )
        return PhaseDetectionResult(
            phase='unknown',
            confidence=0.0,
            evidence=[],
        )


def test_recognition_pipeline_extracts_phase_ocr_texts_from_phase_frame_before_detecting_phase():
    ocr_adapter = PhaseFrameOcrAdapter()
    phase_detector = RecordingTeamSelectPhaseDetector()
    recognizer = ChineseOcrSideRecognizer(ocr_adapter=ocr_adapter)
    pipeline = RecognitionPipeline(phase_detector=phase_detector, recognizer=recognizer)

    result = pipeline.recognize(
        {
            'timestamp': '2026-04-19T14:00:00Z',
            'frame_variants': {
                'phase_frame': {
                    'variant_id': 'phase-team-select',
                    'width': 320,
                    'height': 180,
                    'preview_image_data_url': _make_preview_data_url(width=320, height=180),
                },
                'roi_source_frame': {
                    'variant_id': 'roi-team-select',
                    'width': 1920,
                    'height': 1080,
                    'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
                },
            },
        }
    )

    assert result.current_phase == 'team_select'
    assert ocr_adapter.calls[0]['frame']['variant_id'] == 'phase-team-select'
    assert phase_detector.detect_calls[0]['variant_id'] == 'phase-team-select'
    assert phase_detector.detect_calls[0]['ocr_texts'] == ['请选择出3只要上场战斗的宝可梦。', '选择完毕', '0/3']
    assert '请选择出3只要上场战斗的宝可梦。' in result.phase_evidence


def test_recognition_pipeline_builds_team_select_roi_payloads_after_phase_frame_ocr_detection():
    recognizer = ChineseOcrSideRecognizer(ocr_adapter=PhaseFrameOcrAdapter())
    phase_detector = RecordingTeamSelectPhaseDetector()
    pipeline = RecognitionPipeline(phase_detector=phase_detector, recognizer=recognizer)

    result = pipeline.recognize(
        {
            'timestamp': '2026-04-19T14:01:00Z',
            'frame_variants': {
                'phase_frame': {
                    'variant_id': 'phase-team-select-2',
                    'width': 320,
                    'height': 180,
                    'preview_image_data_url': _make_preview_data_url(width=320, height=180),
                },
                'roi_source_frame': {
                    'variant_id': 'roi-team-select-2',
                    'width': 1920,
                    'height': 1080,
                    'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
                },
            },
        }
    )

    assert result.layout_variant == 'team_select_default'
    assert set(result.roi_payloads.keys()) == {'instruction_banner', 'player_team_list', 'opponent_team_list'}
    assert result.roi_payloads['instruction_banner']['source'] == 'phase-frame'
    assert result.roi_payloads['instruction_banner']['preview_image_data_url'].startswith('data:image/jpeg;base64,')
    assert result.roi_payloads['player_team_list']['source'] == 'roi-source-frame'
    assert result.roi_payloads['player_team_list']['preview_image_data_url'].startswith('data:image/jpeg;base64,')
    assert result.roi_payloads['opponent_team_list']['source'] == 'roi-source-frame'
    assert result.roi_payloads['opponent_team_list']['preview_image_data_url'].startswith('data:image/jpeg;base64,')


class BattlePhaseOcrAdapter:
    def __init__(self):
        self.calls = []

    def read_text(self, frame, roi):
        self.calls.append({'frame': frame, 'roi': roi})
        return [
            {'text': 'COMMAND 38', 'score': 0.99},
            {'text': '招式说明', 'score': 0.98},
            {'text': '魔法闪耀', 'score': 0.96},
            {'text': '雪妖女', 'score': 0.95},
        ]


def test_recognition_pipeline_enters_battle_from_phase_frame_ocr_without_layout_hint_and_builds_battle_rois():
    recognizer = ChineseOcrSideRecognizer(ocr_adapter=BattlePhaseOcrAdapter())
    pipeline = RecognitionPipeline(recognizer=recognizer)

    result = pipeline.recognize(
        {
            'timestamp': '2026-04-19T14:20:00Z',
            'frame_variants': {
                'phase_frame': {
                    'variant_id': 'phase-battle-1',
                    'width': 320,
                    'height': 180,
                    'preview_image_data_url': _make_preview_data_url(width=320, height=180),
                },
                'roi_source_frame': {
                    'variant_id': 'roi-battle-1',
                    'width': 1920,
                    'height': 1080,
                    'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
                },
            },
        }
    )

    assert result.current_phase == 'battle'
    assert result.layout_variant == 'battle_move_menu_open'
    assert 'COMMAND 38' in result.phase_evidence
    assert result.roi_payloads['player_status_panel']['source'] == 'roi-source-frame'
    assert result.roi_payloads['opponent_status_panel']['source'] == 'roi-source-frame'
    assert result.roi_payloads['move_list']['source'] == 'roi-source-frame'


class UnknownPhaseDetector:
    def detect(self, frame):
        from app.schemas.phase import PhaseDetectionResult

        return PhaseDetectionResult(
            phase='unknown',
            confidence=0.0,
            evidence=[],
        )


class NoopRecognizer:
    def recognize_side(self, frame, roi, side):
        return {
            'name': None,
            'confidence': 0.0,
            'source': 'ocr',
            'roi': roi,
            'raw_text': None,
            'matched_by': 'none',
        }


def test_recognition_pipeline_exposes_battle_debug_rois_even_when_phase_is_unknown():
    pipeline = RecognitionPipeline(phase_detector=UnknownPhaseDetector(), recognizer=NoopRecognizer())

    result = pipeline.recognize(
        {
            'timestamp': '2026-04-19T14:21:00Z',
            'frame_variants': {
                'phase_frame': {
                    'variant_id': 'phase-battle-unknown',
                    'width': 320,
                    'height': 180,
                    'preview_image_data_url': _make_preview_data_url(width=320, height=180),
                },
                'roi_source_frame': {
                    'variant_id': 'roi-battle-unknown',
                    'width': 1920,
                    'height': 1080,
                    'preview_image_data_url': _make_preview_data_url(width=1920, height=1080),
                },
            },
        }
    )

    assert result.current_phase == 'unknown'
    assert result.layout_variant == 'battle_move_menu_open'
    assert result.roi_payloads['player_status_panel']['source'] == 'roi-source-frame'
    assert result.roi_payloads['player_status_panel']['pixel_box'] == {
        'left': 90,
        'top': 882,
        'width': 615,
        'height': 184,
    }
    assert result.roi_payloads['player_status_panel']['preview_image_data_url'].startswith('data:image/jpeg;base64,')
    assert result.roi_payloads['opponent_status_panel']['source'] == 'roi-source-frame'
    assert result.roi_payloads['opponent_status_panel']['pixel_box'] == {
        'left': 1365,
        'top': 40,
        'width': 495,
        'height': 162,
    }
    assert result.roi_payloads['opponent_status_panel']['preview_image_data_url'].startswith('data:image/jpeg;base64,')
    assert result.roi_payloads['move_list']['source'] == 'roi-source-frame'
    assert result.roi_payloads['move_list']['pixel_box'] == {
        'left': 1402,
        'top': 464,
        'width': 442,
        'height': 389,
    }
    assert result.roi_payloads['move_list']['preview_image_data_url'].startswith('data:image/jpeg;base64,')
