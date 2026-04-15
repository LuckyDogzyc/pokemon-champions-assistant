from app.services.recognizers.chinese_ocr_recognizer import ChineseOcrSideRecognizer


class StubOcrAdapter:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = 0

    def read_text(self, frame, roi):
        payload = self.payloads[self.calls]
        self.calls += 1
        return payload


def test_chinese_ocr_recognizer_normalizes_alias_and_fuzzy_text():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([
            [{"text": "老喷", "score": 0.92}],
            [{"text": "皮丘卡", "score": 0.81}],
        ])
    )

    player = recognizer.recognize_side({}, {"x": 0, "y": 0, "width": 10, "height": 10}, "player")
    opponent = recognizer.recognize_side({}, {"x": 0, "y": 0, "width": 10, "height": 10}, "opponent")

    assert player["name"] == "喷火龙"
    assert player["source"] == "ocr"
    assert player["confidence"] >= 0.9

    assert opponent["name"] == "皮卡丘"
    assert opponent["source"] == "ocr"
    assert opponent["confidence"] > 0


def test_chinese_ocr_recognizer_returns_empty_result_when_no_text_detected():
    recognizer = ChineseOcrSideRecognizer(ocr_adapter=StubOcrAdapter([[]]))

    result = recognizer.recognize_side({}, {"x": 0, "y": 0, "width": 10, "height": 10}, "player")

    assert result["name"] is None
    assert result["confidence"] == 0.0
    assert result["source"] == "ocr"
