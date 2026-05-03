from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz, process

from app.services.data_loader import load_moves_index
from app.services.recognizers.ocr_adapter import OcrAdapter


class NullOcrAdapter2(OcrAdapter):
    def read_text(self, frame: dict, roi: dict[str, int]) -> list[dict]:
        return []


_PP_PATTERN = re.compile(r'(?:PP|pp)?\s*(\d+)\s*[/:/]\s*(\d+)', re.IGNORECASE)
_NUMERIC_ONLY = re.compile(r'^[\d/%]+\s*$')


class MoveNameMatcher:
    """Small matcher backed by moves_index.json, not Pokémon names."""

    def __init__(self) -> None:
        self._canonical_by_choice: dict[str, str] = {}
        for move_id, info in load_moves_index().items():
            names = [info.get('name_zh'), info.get('name_en'), info.get('name'), move_id]
            for raw_name in names:
                name = str(raw_name or '').strip()
                if name:
                    self._canonical_by_choice[name] = str(info.get('name') or name)

    def match(self, text: str) -> tuple[str | None, float]:
        cleaned = text.strip()
        if not cleaned:
            return None, 0.0
        if cleaned in self._canonical_by_choice:
            return self._canonical_by_choice[cleaned], 1.0
        match = process.extractOne(
            cleaned,
            self._canonical_by_choice.keys(),
            scorer=fuzz.WRatio,
            score_cutoff=82,
        )
        if not match:
            return None, 0.0
        choice, score, _ = match
        return self._canonical_by_choice[choice], score / 100


class MoveListRecognizer:

    """识别战斗画面中的 4 个技能格，每格提取技能名 + 剩余 PP。"""

    def __init__(self, ocr_adapter: OcrAdapter | None = None, matcher: MoveNameMatcher | None = None) -> None:
        self._ocr_adapter = ocr_adapter or NullOcrAdapter2()
        self._matcher = matcher or MoveNameMatcher()

    def recognize_slot(self, roi_frame: dict) -> dict[str, Any]:
        """识别单个技能格，返回 {name, pp_current, pp_max, confidence, debug_raw_text}"""
        texts = self._ocr_adapter.read_text(
            roi_frame,
            {'x': 0, 'y': 0, 'w': roi_frame.get('width', 0), 'h': roi_frame.get('height', 0)}
        )
        raw_texts = [str(t.get('text', '')).strip() for t in texts if str(t.get('text', '')).strip()]

        result: dict[str, Any] = {
            'name': None,
            'pp_current': None,
            'pp_max': None,
            'confidence': 0.0,
            'debug_raw_text': ' | '.join(raw_texts) if raw_texts else None,
        }

        # 1. 提取 PP 值（如 "PP 5/8" -> current=5, max=8）
        for t in raw_texts:
            m = _PP_PATTERN.search(t)
            if m:
                result['pp_current'] = int(m.group(1))
                result['pp_max'] = int(m.group(2))
                break

        # 2. 找技能名称——排除 PP 数字和纯数字文本
        for t in raw_texts:
            cleaned = t.strip()
            if not cleaned:
                continue
            if _NUMERIC_ONLY.match(cleaned):
                continue
            if _PP_PATTERN.match(cleaned):
                continue
            matched_name, confidence = self._matcher.match(cleaned)
            if matched_name:
                result['name'] = matched_name
                result['confidence'] = max(0.8, confidence)
                break

        # 3. 如果没有通过 name matcher 命中，保留原始文本作为技能名
        if not result['name']:
            for t in raw_texts:
                cleaned = t.strip()
                if not cleaned or _NUMERIC_ONLY.match(cleaned) or _PP_PATTERN.match(cleaned):
                    continue
                result['name'] = cleaned
                result['confidence'] = 0.5
                break

        return result

    def recognize_all(self, roi_frames: dict[str, dict]) -> list[dict[str, Any]]:
        """识别全部 4 个技能格"""
        results = []
        for i in range(1, 5):
            key = f'move_slot_{i}'
            roi = roi_frames.get(key, {})
            results.append(self.recognize_slot(roi))
        return results
