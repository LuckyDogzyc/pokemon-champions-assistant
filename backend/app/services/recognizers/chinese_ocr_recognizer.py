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

    _STATUS_NOISE_TOKENS = {'查看状态', '招式说明', '超级进化'}
    _MOVE_LIST_NOISE_TOKENS = {'查看状态', '招式说明', '有效果', '效果不好', '超级进化', '战斗', '宝可梦'}
    _NON_NAME_TOKENS = {'♂', '♀'}
    _STATUS_ABNORMAL_KEYWORDS = ['中毒', '麻痹', '烧伤', '冰冻', '睡眠', '混乱', '寄生', '中剧毒']
    _HP_PATTERN = re.compile(r'(\d+)\s*/\s*(\d+)')
    _PERCENT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*%')
    _LV_PATTERN = re.compile(r'(?:Lv|LV|lv|Lvl|LVL)\.?\s*(\d+)')

    def recognize_named_roi(self, frame: dict, roi: dict[str, int], roi_name: str) -> dict | None:
        if roi_name == 'move_list':
            return self._recognize_move_list(frame, roi)
        if roi_name in ('player_status_panel', 'opponent_status_panel'):
            return self._recognize_status_panel(frame, roi, roi_name)
        return None

    def _recognize_move_list(self, frame: dict, roi: dict[str, int]) -> dict:
        texts = self._ocr_adapter.read_text(frame, roi)
        recognized_texts = self._extract_move_list_candidates(texts)
        return {
            'recognized_texts': recognized_texts,
            'recognized_count': len(recognized_texts),
            'matched_by': 'ocr-text-list',
        }

    def _recognize_status_panel(self, frame: dict, roi: dict[str, int], roi_name: str) -> dict:
        texts = self._ocr_adapter.read_text(frame, roi)
        result: dict[str, object] = {
            'matched_by': 'ocr-status-panel',
        }

        # Extract pokemon name
        name = self._extract_pokemon_name(texts)
        if name:
            result['pokemon_name'] = name

        # Extract HP (e.g. "120/150")
        hp_text = self._extract_hp(texts)
        if hp_text:
            result['hp_text'] = hp_text

        # Extract percentage (e.g. "80%")
        pct = self._extract_percentage(texts)
        if pct:
            result['hp_percentage'] = pct

        # Extract level (e.g. "Lv.50")
        level = self._extract_level(texts)
        if level:
            result['level'] = level

        # Extract status abnormality (e.g. "中毒")
        abnormal = self._extract_status_abnormality(texts)
        if abnormal:
            result['status_abnormality'] = abnormal

        # Also store all raw texts for debugging
        raw = [item.get('text', '') for item in texts if item.get('text')]
        result['raw_texts'] = raw
        result['raw_count'] = len(raw)

        return result

    def _extract_pokemon_name(self, texts: list[dict]) -> str | None:
        for item in sorted(texts, key=lambda e: float(e.get('score', 0.0)), reverse=True):
            text = str(item.get('text', '')).strip()
            if not text:
                continue
            if PURE_NUMERIC_PATTERN.match(text):
                continue
            if text in self._NON_NAME_TOKENS:
                continue
            if text.upper().startswith('COMMAND'):
                continue
            if any(token in text for token in self._STATUS_NOISE_TOKENS):
                continue
            if self._HP_PATTERN.search(text):
                continue
            if self._PERCENT_PATTERN.search(text):
                continue
            if self._LV_PATTERN.search(text):
                continue
            matched = self._matcher.match(text)
            if matched.found:
                return matched.canonical_name
        # Fallback: return first non-noise text
        for item in sorted(texts, key=lambda e: float(e.get('score', 0.0)), reverse=True):
            text = str(item.get('text', '')).strip()
            if not text:
                continue
            if PURE_NUMERIC_PATTERN.match(text):
                continue
            if text in self._NON_NAME_TOKENS:
                continue
            if text.upper().startswith('COMMAND'):
                continue
            if any(token in text for token in self._STATUS_NOISE_TOKENS):
                continue
            if self._HP_PATTERN.search(text):
                continue
            if self._PERCENT_PATTERN.search(text):
                continue
            if self._LV_PATTERN.search(text):
                continue
            return text
        return None

    def _extract_hp(self, texts: list[dict]) -> str | None:
        for item in texts:
            text = str(item.get('text', '')).strip()
            m = self._HP_PATTERN.search(text)
            if m:
                return f'{m.group(1)}/{m.group(2)}'

            normalized = self._normalize_repeated_hp_digits(text)
            if normalized:
                return normalized
        return None

    def _normalize_repeated_hp_digits(self, text: str) -> str | None:
        digits = ''.join(ch for ch in text if ch.isdigit())
        if len(digits) < 5 or len(digits) % 2 == 0:
            return None

        half = len(digits) // 2
        left = digits[:half]
        right = digits[half + 1:]
        if left and left == right:
            return f'{left}/{right}'
        return None

    def _extract_percentage(self, texts: list[dict]) -> str | None:
        for item in texts:
            text = str(item.get('text', '')).strip()
            m = self._PERCENT_PATTERN.search(text)
            if m:
                return f'{m.group(1)}%'
        return None

    def _extract_level(self, texts: list[dict]) -> str | None:
        for item in texts:
            text = str(item.get('text', '')).strip()
            m = self._LV_PATTERN.search(text)
            if m:
                return f'Lv.{m.group(1)}'
        return None

    def _extract_status_abnormality(self, texts: list[dict]) -> str | None:
        for item in texts:
            text = str(item.get('text', '')).strip()
            for keyword in self._STATUS_ABNORMAL_KEYWORDS:
                if keyword in text:
                    return keyword
        return None

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

    def _extract_move_list_candidates(self, texts: list[dict]) -> list[str]:
        candidates: list[str] = []
        for item in sorted(texts, key=lambda entry: float(entry.get('score', 0.0)), reverse=True):
            text = str(item.get('text', '')).strip()
            if not text:
                continue
            if PURE_NUMERIC_PATTERN.match(text):
                continue
            if text.upper().startswith('COMMAND'):
                continue
            if any(token in text for token in self._MOVE_LIST_NOISE_TOKENS):
                continue
            if text not in candidates:
                candidates.append(text)
            if len(candidates) >= 4:
                break
        return candidates

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
