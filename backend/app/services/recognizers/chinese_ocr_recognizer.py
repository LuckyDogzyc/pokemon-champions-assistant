from __future__ import annotations

from app.services.name_matcher import NameMatcher
from app.services.recognizers.base import BaseSideRecognizer
from app.services.recognizers.ocr_adapter import OcrAdapter


class NullOcrAdapter(OcrAdapter):
    def read_text(self, frame: dict, roi: dict[str, int]) -> list[dict]:
        return []


class ChineseOcrSideRecognizer(BaseSideRecognizer):
    def __init__(self, ocr_adapter: OcrAdapter | None = None, matcher: NameMatcher | None = None) -> None:
        self._ocr_adapter = ocr_adapter or NullOcrAdapter()
        self._matcher = matcher or NameMatcher()

    def recognize_side(self, frame: dict, roi: dict[str, int], side: str) -> dict:
        texts = self._ocr_adapter.read_text(frame, roi)
        if not texts:
            return {"name": None, "confidence": 0.0, "source": "ocr", "roi": roi}

        best = max(texts, key=lambda item: float(item.get("score", 0.0)))
        raw_text = str(best.get("text", "")).strip()
        raw_score = float(best.get("score", 0.0))
        matched = self._matcher.match(raw_text)
        if not matched.found:
            return {"name": None, "confidence": 0.0, "source": "ocr", "roi": roi}

        normalized_confidence = max(raw_score, matched.score / 100.0)
        return {
            "name": matched.canonical_name,
            "confidence": round(normalized_confidence, 4),
            "source": "ocr",
            "roi": roi,
        }
