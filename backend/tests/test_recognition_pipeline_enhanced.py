from app.services.recognition_pipeline import RecognitionPipeline


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
