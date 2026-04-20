from app.services.recognizers.paddle_ocr_adapter import PaddleOcrAdapter, _normalize_paddle_result


class StubOcrEngine:
    def ocr(self, image, cls=False):
        return [[[[0, 0], [1, 0], [1, 1], [0, 1]], ("喷火龙", 0.97)]]


def test_normalize_paddle_result_with_standard_output():
    normalized = _normalize_paddle_result([[[[0, 0], [1, 0], [1, 1], [0, 1]], ("皮卡丘", 0.88)]])

    assert normalized == [{"text": "皮卡丘", "score": 0.88}]


def test_paddle_ocr_adapter_returns_normalized_texts(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    monkeypatch.setattr(
        paddle_ocr_adapter,
        "build_roi_frame",
        lambda frame, roi: {"preview_image_data_url": "data:image/jpeg;base64,stub"},
    )
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter(ocr_engine=StubOcrEngine())
    result = adapter.read_text({"width": 1920, "height": 1080}, {"x": 0, "y": 0, "w": 1, "h": 1})

    assert result == [{"text": "喷火龙", "score": 0.97}]


def test_paddle_ocr_adapter_uses_pre_cropped_roi_frame_without_recropping(monkeypatch):
    from app.services.recognizers import paddle_ocr_adapter

    def fail_if_recrop(frame, roi):
        raise AssertionError("should not crop an already-cropped roi frame")

    monkeypatch.setattr(paddle_ocr_adapter, "build_roi_frame", fail_if_recrop)
    monkeypatch.setattr(paddle_ocr_adapter, "_decode_preview_image", lambda _: object())

    adapter = PaddleOcrAdapter(ocr_engine=StubOcrEngine())
    result = adapter.read_text(
        {
            "width": 48,
            "height": 32,
            "preview_image_data_url": "data:image/jpeg;base64,stub",
            "source_preview_image_data_url": "data:image/jpeg;base64,source-stub",
            "pixel_box": {"left": 10, "top": 20, "width": 48, "height": 32},
        },
        {"x": 0.7, "y": 0.42, "w": 0.24, "h": 0.32},
    )

    assert result == [{"text": "喷火龙", "score": 0.97}]
