from __future__ import annotations

import re
from typing import Any

from app.services.name_matcher import NameMatcher
from app.services.recognizers.ocr_adapter import OcrAdapter


class NullOcrAdapter2(OcrAdapter):
    def read_text(self, frame: dict, roi: dict[str, int]) -> list[dict]:
        return []


_PP_PATTERN = re.compile(r'(?:PP|pp)?\s*(\d+)\s*[/:/]\s*(\d+)', re.IGNORECASE)
_NUMERIC_ONLY = re.compile(r'^[\d/%]+\s*$')


class MoveListRecognizer:
    """识别战斗画面中的 4 个技能格，每格提取技能名 + 剩余 PP。"""

    def __init__(self, ocr_adapter: OcrAdapter | None = None, matcher: NameMatcher | None = None) -> None:
        self._ocr_adapter = ocr_adapter or NullOcrAdapter2()
        self._matcher = matcher or NameMatcher()

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
            # 通过 name matcher 匹配已知技能名称（当前按宝可梦名称匹配）
            matched = self._matcher.match(cleaned)
            if matched and matched.found:
                result['name'] = matched.canonical_name
                result['confidence'] = 0.9
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
