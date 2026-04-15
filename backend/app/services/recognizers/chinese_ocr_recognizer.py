from __future__ import annotations

import re

from app.services.name_matcher import NameMatcher
from app.services.recognizers.base import BaseSideRecognizer
from app.services.recognizers.ocr_adapter import OcrAdapter


PURE_NUMERIC_PATTERN = re.compile(r'^[\d:%./]+$')


class NullOcrAdapter(OcrAdapter):
    def read_text(self, frame: dict, roi: dict[str, int]) -> list[dict]:
        return []


class ChineseOcrSideRecognizer(BaseSideRecognizer):
    def __init__(self, ocr_adapter: OcrAdapter | None = None, matcher: NameMatcher | None = None) -> None:
        self._ocr_adapter = ocr_adapter or NullOcrAdapter()
        self._matcher = matcher or NameMatcher()

    def recognize_side(self, frame: dict, roi: dict[str, int], side: str) -> dict:
        texts = self._ocr_adapter.read_text(frame, roi)
        noise_texts = set(frame.get("annotation_noise_texts", []))
        candidates = self._filter_candidates(texts, noise_texts)
        if not candidates:
            return {
                "name": None,
                "confidence": 0.0,
                "source": "ocr",
                "roi": roi,
                "raw_text": None,
                "matched_by": "none",
            }

        for candidate in candidates:
            raw_text = candidate["text"]
            raw_score = candidate["score"]
            matched = self._matcher.match(raw_text)
            if not matched.found:
                continue
            normalized_confidence = max(raw_score, matched.score / 100.0)
            return {
                "name": matched.canonical_name,
                "confidence": round(normalized_confidence, 4),
                "source": "ocr",
                "roi": roi,
                "raw_text": raw_text,
                "matched_by": matched.match_type,
            }

        return {
            "name": None,
            "confidence": 0.0,
            "source": "ocr",
            "roi": roi,
            "raw_text": candidates[0]["text"],
            "matched_by": "none",
        }

    def _filter_candidates(self, texts: list[dict], noise_texts: set[str]) -> list[dict[str, float | str]]:
        filtered: list[dict[str, float | str]] = []
        for item in sorted(texts, key=lambda entry: float(entry.get("score", 0.0)), reverse=True):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            if text in noise_texts:
                continue
            if PURE_NUMERIC_PATTERN.match(text):
                continue
            if text.upper().startswith("COMMAND"):
                continue
            if any(token in text for token in ["查看状态", "招式说明", "有效果", "效果不好", "超级进化"]):
                continue
            filtered.append({"text": text, "score": float(item.get("score", 0.0))})
        return filtered
