from app.services.recognizers.chinese_ocr_recognizer import ChineseOcrSideRecognizer


class StubOcrAdapter:
    def __init__(self, payloads):
        self.payloads = payloads

    def read_text(self, frame, roi):
        return self.payloads


def test_chinese_ocr_recognizer_filters_noise_and_uses_next_valid_candidate():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter(
            [
                {'text': 'COMMAND 43', 'score': 0.99},
                {'text': '查看状态', 'score': 0.96},
                {'text': '老喷', 'score': 0.88},
            ]
        )
    )

    result = recognizer.recognize_side(
        {'annotation_noise_texts': ['COMMAND 43', '查看状态']},
        {'x': 0, 'y': 0, 'width': 10, 'height': 10},
        'player',
    )

    assert result['name'] == '喷火龙'
    assert result['raw_text'] == '老喷'
    assert result['matched_by'] == 'alias'


def test_chinese_ocr_recognizer_ignores_numeric_and_percentage_only_candidates():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter(
            [
                {'text': '100%', 'score': 0.99},
                {'text': '07:00', 'score': 0.95},
                {'text': '雪妖女', 'score': 0.80},
            ]
        )
    )

    result = recognizer.recognize_side({}, {'x': 0, 'y': 0, 'width': 10, 'height': 10}, 'opponent')

    assert result['name'] == '雪妖女'
    assert result['raw_text'] == '雪妖女'
    assert result['matched_by'] == 'exact'
