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


def test_chinese_ocr_recognizer_extracts_move_list_texts_for_named_roi():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([
            [
                {"text": "COMMAND 43", "score": 0.99},
                {"text": "招式说明", "score": 0.97},
                {"text": "日光束", "score": 0.95},
                {"text": "魔法闪耀", "score": 0.94},
                {"text": "光合作用", "score": 0.93},
                {"text": "气象球", "score": 0.92},
                {"text": "有效果", "score": 0.91},
                {"text": "超级进化", "score": 0.90},
            ]
        ])
    )

    result = recognizer.recognize_named_roi(
        {},
        {"x": 0.73, "y": 0.43, "w": 0.23, "h": 0.36},
        "move_list",
    )

    assert result == {
        "recognized_texts": ["日光束", "魔法闪耀", "光合作用", "气象球"],
        "recognized_count": 4,
        "matched_by": "ocr-text-list",
    }


def test_chinese_ocr_recognizer_extracts_status_panel_with_name_hp_and_level():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([
            [
                {"text": "烈咬陆鲨", "score": 0.96},
                {"text": "HP 120/150", "score": 0.94},
                {"text": "Lv.50", "score": 0.93},
                {"text": "80%", "score": 0.91},
                {"text": "中毒", "score": 0.88},
            ]
        ])
    )

    result = recognizer.recognize_named_roi(
        {},
        {"x": 0.02, "y": 0.78, "w": 0.25, "h": 0.14},
        "player_status_panel",
    )

    assert result is not None
    assert result["matched_by"] == "ocr-status-panel"
    assert result["pokemon_name"] == "烈咬陆鲨"
    assert result["hp_text"] == "120/150"
    assert result["hp_percentage"] == "80%"
    assert result["level"] == "Lv.50"
    assert result["status_abnormality"] == "中毒"
    assert result["raw_count"] == 5


def test_chinese_ocr_recognizer_status_panel_with_fuzzy_name():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([
            [
                {"text": "老喷", "score": 0.90},
                {"text": "HP 200/266", "score": 0.92},
                {"text": "75%", "score": 0.88},
            ]
        ])
    )

    result = recognizer.recognize_named_roi(
        {},
        {"x": 0.69, "y": 0.03, "w": 0.28, "h": 0.13},
        "opponent_status_panel",
    )

    assert result is not None
    assert result["pokemon_name"] == "喷火龙"
    assert result["hp_text"] == "200/266"
    assert result["hp_percentage"] == "75%"


def test_chinese_ocr_recognizer_status_panel_minimal_data():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([
            [
                {"text": "雪妖女", "score": 0.85},
            ]
        ])
    )

    result = recognizer.recognize_named_roi(
        {},
        {"x": 0.69, "y": 0.03, "w": 0.28, "h": 0.13},
        "opponent_status_panel",
    )

    assert result is not None
    assert result["pokemon_name"] == "雪妖女"
    assert "hp_text" not in result
    assert "hp_percentage" not in result
    assert "status_abnormality" not in result


def test_chinese_ocr_recognizer_status_panel_filters_noise():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([
            [
                {"text": "COMMAND 43", "score": 0.99},
                {"text": "查看状态", "score": 0.98},
                {"text": "大竺葵", "score": 0.95},
                {"text": "HP 80/100", "score": 0.93},
            ]
        ])
    )

    result = recognizer.recognize_named_roi(
        {},
        {"x": 0.02, "y": 0.78, "w": 0.25, "h": 0.14},
        "player_status_panel",
    )

    assert result is not None
    assert result["pokemon_name"] == "大竺葵"
    assert result["hp_text"] == "80/100"


def test_chinese_ocr_recognizer_returns_none_for_unknown_roi_name():
    recognizer = ChineseOcrSideRecognizer(
        ocr_adapter=StubOcrAdapter([[]])
    )

    result = recognizer.recognize_named_roi(
        {},
        {"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1},
        "command_panel",
    )

    assert result is None
