from __future__ import annotations

from app.services.recognizers.base import BaseSideRecognizer


class MockSideRecognizer(BaseSideRecognizer):
    def recognize_side(self, frame: dict, roi: dict[str, int], side: str) -> dict:
        if side == "player":
            return {"name": "喷火龙", "confidence": 0.99, "source": "mock", "roi": roi}
        return {"name": "皮卡丘", "confidence": 0.88, "source": "mock", "roi": roi}
