from __future__ import annotations

import re
from typing import Any

from app.services.name_matcher import NameMatcher
from app.services.recognizers.ocr_adapter import OcrAdapter


class NullOcrAdapter(OcrAdapter):
    def read_text(self, frame: dict, roi: dict[str, int]) -> list[dict]:
        return []


_GENDER_PATTERN = re.compile(r'[♂♀]')
_PP_PATTERN = re.compile(r'(?:PP|pp)?\s*(\d+)\s*[/:/]\s*(\d+)', re.IGNORECASE)
_ITEM_PATTERN = re.compile(r'[携带道具]{0,4}[:：]?\s*(.+?)(?=\s*[♂♀]|$)')


class TeamSelectRecognizer:
    """识别选人界面中每只宝可梦的名称、道具和性别。

    每只宝可梦的 ROI 截图应包含：
    - 宝可梦图标（左侧）
    - 名称文本（图标右侧）
    - 道具文本（名称下方）
    - 性别符号（♂/♀，通常在名称附近）
    """

    def __init__(self, ocr_adapter: OcrAdapter | None = None, matcher: NameMatcher | None = None) -> None:
        self._ocr_adapter = ocr_adapter or NullOcrAdapter()
        self._matcher = matcher or NameMatcher()

    def recognize_slot(self, roi_frame: dict, slot_name: str) -> dict[str, Any]:
        """对单个选人 slot 做 OCR，返回 {name, item, gender, debug_raw_text}"""
        texts = self._ocr_adapter.read_text(roi_frame, {'x': 0, 'y': 0, 'w': roi_frame.get('width', 0), 'h': roi_frame.get('height', 0)})
        raw_texts = [str(t.get('text', '')).strip() for t in texts if str(t.get('text', '')).strip()]

        result: dict[str, Any] = {
            'name': None,
            'item': None,
            'gender': None,
            'debug_raw_text': ' | '.join(raw_texts) if raw_texts else None,
        }

        # 1. 找性别符号
        gender = None
        for t in raw_texts:
            m = _GENDER_PATTERN.search(t)
            if m:
                gender = 'male' if m.group() == '♂' else 'female'
                break
        result['gender'] = gender

        # 2. 找宝可梦名称——通过 name matcher 模糊匹配
        for t in raw_texts:
            cleaned = _GENDER_PATTERN.sub('', t).strip()
            if not cleaned:
                continue
            matched = self._matcher.match(cleaned)
            if matched and matched.found:
                result['name'] = matched.canonical_name
                break

        # 3. 如果没有直接命中的名称匹配，尝试从文本中提取
        if not result['name']:
            for t in raw_texts:
                cleaned = _GENDER_PATTERN.sub('', t).strip()
                if not cleaned or _PP_PATTERN.match(cleaned):
                    continue
                matched = self._matcher.match(cleaned)
                if matched and matched.found:
                    result['name'] = matched.canonical_name
                    break

        # 4. 找道具文本——排除已知名称和性别符号后的文本
        non_name_texts = []
        for t in raw_texts:
            cleaned = _GENDER_PATTERN.sub('', t).strip()
            if not cleaned:
                continue
            if result['name']:
                check_match = self._matcher.match(cleaned)
                if check_match and check_match.found and check_match.canonical_name == result['name']:
                    continue
            if _PP_PATTERN.match(cleaned):
                continue
            non_name_texts.append(cleaned)

        if non_name_texts:
            # 道具通常是较短的文本（不含数字/百分号）
            for t in non_name_texts:
                if re.search(r'[道具]', t) or (len(t) <= 10 and not re.search(r'\d', t)):
                    result['item'] = t
                    break
            if not result['item'] and non_name_texts:
                result['item'] = non_name_texts[0]

        return result

    def recognize_all_player(self, roi_frames: dict[str, dict]) -> list[dict[str, Any]]:
        """识别全部 6 个我方 slot"""
        results = []
        for i in range(1, 7):
            key = f'player_mon_{i}'
            roi = roi_frames.get(key, {})
            results.append(self.recognize_slot(roi, key))
        return results

    def recognize_all_opponent(self, roi_frames: dict[str, dict]) -> list[dict[str, Any]]:
        """识别全部 6 个对方 slot（通过缩略图匹配）"""
        results = []
        for i in range(1, 7):
            key = f'opponent_mon_{i}'
            roi = roi_frames.get(key, {})
            results.append(self.recognize_slot(roi, key))
        return results
