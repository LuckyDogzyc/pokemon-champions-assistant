from __future__ import annotations

import threading

from app.schemas.phase import BattlePhase
from app.schemas.recognition import (
    RecognitionSource,
    RecognitionStatePayload,
    RecognizedSide,
    TeamPreviewState,
)
from app.services.frame_variants import resolve_frame_variants
from app.services.layout_anchors import DEFAULT_LAYOUTS, get_battle_name_anchors, get_layout_anchors
from app.services.phase_detector import PhaseDetector
from app.services.recognizers.mock_recognizer import MockSideRecognizer
from app.services.roi_capture import build_roi_frame, enrich_roi_payloads_with_crops


def build_phase_snapshot(*, phase: str, confidence: float, evidence: list[str]) -> dict[str, str | float | list[str]]:
    return {
        'phase': phase,
        'confidence': confidence,
        'evidence': list(evidence),
    }


def build_roi_payloads(frame: dict, *, phase: str, layout_variant: str | None) -> dict[str, dict[str, object]]:
    anchors = get_layout_anchors({**frame, 'layout_variant': layout_variant, 'layout_variant_hint': layout_variant})

    if phase == BattlePhase.TEAM_SELECT:
        payloads: dict[str, dict[str, float | str | int | None]] = {}
        # 保留原有横幅检测
        for key in ('instruction_banner',):
            if key not in anchors:
                continue
            payloads[key] = {
                **anchors[key],
                'role': 'phase-detection',
                'source': 'phase-frame',
                'layout_variant': layout_variant,
            }
        # 全流程追踪 v2：我方 6 只 + 对方 6 只独立 ROI
        for side in ('player', 'opponent'):
            for i in range(1, 7):
                key = f'{side}_mon_{i}'
                if key not in anchors:
                    continue
                payloads[key] = {
                    **anchors[key],
                    'role': f'team-select-{side}-slot-{i}',
                    'source': 'roi-source-frame',
                    'layout_variant': layout_variant,
                }
        return payloads

    if phase == BattlePhase.BATTLE:
        payloads = {}
        for key, role in {
            'player_status_panel': 'battle-player-status-panel',
            'opponent_status_panel': 'battle-opponent-status-panel',
            'move_list': 'battle-move-list',
            # 全流程追踪 v2：HP 区域
            'player_hp_text': 'battle-player-hp-text',
            'opponent_hp_bar': 'battle-opponent-hp-bar',
            # 全流程追踪 v2：技能 4 分格
            'move_slot_1': 'battle-move-slot-1',
            'move_slot_2': 'battle-move-slot-2',
            'move_slot_3': 'battle-move-slot-3',
            'move_slot_4': 'battle-move-slot-4',
        }.items():
            if key not in anchors:
                continue
            payloads[key] = {
                **anchors[key],
                'role': role,
                'source': 'roi-source-frame',
                'layout_variant': layout_variant,
            }
        return payloads

    return {}


class RecognitionPipeline:
    def __init__(self, phase_detector=None, recognizer=None) -> None:
        self._phase_detector = phase_detector or PhaseDetector()
        self._recognizer = recognizer or MockSideRecognizer()
        self._last_result = RecognitionStatePayload(timestamp='')
        self._recognize_lock = threading.Lock()

    def _extract_phase_ocr_texts(self, frame: dict) -> list[str]:
        if frame.get('ocr_texts'):
            return [str(item).strip() for item in frame.get('ocr_texts', []) if str(item).strip()]

        ocr_adapter = getattr(self._recognizer, '_ocr_adapter', None)
        read_text = getattr(ocr_adapter, 'read_text', None)
        if not callable(read_text):
            return []

        width = int(frame.get('width') or 0)
        height = int(frame.get('height') or 0)
        if width <= 0 or height <= 0:
            return []

        raw_items = read_text(frame, {'x': 0, 'y': 0, 'w': width, 'h': height}) or []
        return [str(item.get('text', '')).strip() for item in raw_items if str(item.get('text', '')).strip()]

    def _infer_layout_variant_from_phase_context(self, phase: str, layout_variant: str | None, phase_ocr_texts: list[str]) -> str | None:
        if layout_variant:
            return layout_variant
        if phase == BattlePhase.TEAM_SELECT:
            return 'team_select_default' if 'team_select_default' in DEFAULT_LAYOUTS else layout_variant
        if phase != BattlePhase.BATTLE:
            return layout_variant

        texts = [str(item).strip() for item in phase_ocr_texts if str(item).strip()]
        if any(text.upper().startswith('COMMAND') for text in texts) and any('招式说明' in text for text in texts):
            return 'battle_move_menu_open' if 'battle_move_menu_open' in DEFAULT_LAYOUTS else layout_variant
        if any(text.upper().startswith('COMMAND') for text in texts):
            return 'battle_default' if 'battle_default' in DEFAULT_LAYOUTS else layout_variant
        return layout_variant

    def _enrich_roi_payloads(self, frame: dict, roi_payloads: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
        enriched_payloads = enrich_roi_payloads_with_crops(frame, roi_payloads)
        recognize_named_roi = getattr(self._recognizer, 'recognize_named_roi', None)
        if not callable(recognize_named_roi):
            return enriched_payloads

        for roi_name, payload in enriched_payloads.items():
            if roi_name not in ('move_list', 'player_status_panel', 'opponent_status_panel'):
                continue
            roi_frame = build_roi_frame(frame, payload)
            if roi_frame is None:
                continue
            recognized = recognize_named_roi(roi_frame, payload, roi_name)
            if isinstance(recognized, dict) and recognized:
                payload.update(recognized)
        return enriched_payloads

    def recognize(self, frame: dict) -> RecognitionStatePayload:
        with self._recognize_lock:
            return self._recognize_locked(frame)

    def _recognize_locked(self, frame: dict) -> RecognitionStatePayload:
        frame_variants = resolve_frame_variants(frame)
        phase_frame = dict(frame_variants.phase_frame)
        roi_source_frame = frame_variants.roi_source_frame
        phase_ocr_texts = self._extract_phase_ocr_texts(phase_frame)
        if phase_ocr_texts:
            phase_frame['ocr_texts'] = phase_ocr_texts
        phase_result = self._phase_detector.detect(phase_frame)
        layout_variant = (
            frame.get('layout_variant')
            or frame.get('layout_variant_hint')
            or phase_frame.get('layout_variant')
            or phase_frame.get('layout_variant_hint')
            or roi_source_frame.get('layout_variant')
            or roi_source_frame.get('layout_variant_hint')
        )
        layout_variant = self._infer_layout_variant_from_phase_context(
            str(phase_result.phase),
            layout_variant,
            phase_ocr_texts,
        )
        fallback_battle_debug_layout = (
            layout_variant is None
            and phase_result.phase == BattlePhase.UNKNOWN
            and bool(roi_source_frame.get('preview_image_data_url'))
        )
        if fallback_battle_debug_layout:
            layout_variant = 'battle_move_menu_open' if 'battle_move_menu_open' in DEFAULT_LAYOUTS else 'battle_default'
        phase_snapshot = build_phase_snapshot(
            phase=str(phase_result.phase),
            confidence=float(phase_result.confidence),
            evidence=list(phase_result.evidence),
        )
        roi_phase = str(phase_result.phase)
        if fallback_battle_debug_layout:
            roi_phase = BattlePhase.BATTLE
        roi_payloads = self._enrich_roi_payloads(
            roi_source_frame,
            build_roi_payloads(roi_source_frame, phase=roi_phase, layout_variant=layout_variant),
        )

        if phase_result.phase == BattlePhase.TEAM_SELECT:
            annotation_target = frame.get('annotation_target', {})
            # 全流程追踪 v2：识别选人 slot
            from app.services.recognizers.team_select_recognizer import TeamSelectRecognizer
            team_recognizer = TeamSelectRecognizer(
                ocr_adapter=getattr(self._recognizer, '_ocr_adapter', None),
                matcher=getattr(self._recognizer, '_matcher', None),
            )
            player_slots = team_recognizer.recognize_all_player(roi_payloads)
            opponent_slots = team_recognizer.recognize_all_opponent(roi_payloads)
            from app.schemas.recognition import RecognizedTeamSlot
            result = RecognitionStatePayload(
                current_phase=phase_result.phase,
                timestamp=frame.get('timestamp', ''),
                layout_variant=layout_variant,
                phase_evidence=list(phase_result.evidence),
                phase_snapshot=phase_snapshot,
                roi_payloads=roi_payloads,
                team_preview=TeamPreviewState(
                    player_team=list(annotation_target.get('player_team', [])),
                    opponent_team=list(annotation_target.get('opponent_team', [])),
                    selected_count=annotation_target.get('selected_count'),
                    instruction_text=annotation_target.get('instruction_text'),
                ),
                player_team_slots=[RecognizedTeamSlot(**s) for s in player_slots],
                opponent_team_slots=[RecognizedTeamSlot(**s) for s in opponent_slots],
            )
            self._last_result = result
            return result

        if phase_result.phase != BattlePhase.BATTLE:
            result = RecognitionStatePayload(
                current_phase=phase_result.phase,
                timestamp=frame.get('timestamp', ''),
                layout_variant=layout_variant,
                phase_evidence=list(phase_result.evidence),
                phase_snapshot=phase_snapshot,
                roi_payloads=roi_payloads,
            )
            self._last_result = result
            return result

        anchors = get_battle_name_anchors(
            {**roi_source_frame, 'layout_variant': layout_variant, 'layout_variant_hint': layout_variant}
        )
        player = self._recognizer.recognize_side(roi_source_frame, anchors['player'], 'player')
        opponent = self._recognizer.recognize_side(roi_source_frame, anchors['opponent'], 'opponent')

        # 全流程追踪 v2：HP 和技能识别
        player_hp_current = None
        player_hp_max = None
        opponent_hp_percent = None
        revealed_moves = []

        from app.services.recognizers.move_list_recognizer import MoveListRecognizer
        move_recognizer = MoveListRecognizer(
            ocr_adapter=getattr(self._recognizer, '_ocr_adapter', None),
            matcher=getattr(self._recognizer, '_matcher', None),
        )
        revealed_moves = move_recognizer.recognize_all(roi_payloads)

        # 从 ROI payloads 中提取 HP 信息（如果已有 OCR 结果）
        hp_payload = roi_payloads.get('player_hp_text', {})
        if hp_payload.get('ocr_text'):
            import re
            hp_match = re.search(r'(\d+)\s*/\s*(\d+)', str(hp_payload.get('ocr_text', '')))
            if hp_match:
                player_hp_current = int(hp_match.group(1))
                player_hp_max = int(hp_match.group(2))

        opp_hp_payload = roi_payloads.get('opponent_hp_bar', {})
        if opp_hp_payload.get('ocr_text'):
            import re
            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', str(opp_hp_payload.get('ocr_text', '')))
            if pct_match:
                opponent_hp_percent = float(pct_match.group(1))

        result = RecognitionStatePayload(
            current_phase=phase_result.phase,
            layout_variant=layout_variant,
            phase_evidence=list(phase_result.evidence),
            phase_snapshot=phase_snapshot,
            roi_payloads=roi_payloads,
            player=RecognizedSide(
                name=player.get('name'),
                confidence=player.get('confidence', 0.0),
                source=RecognitionSource(player.get('source', 'mock')),
                debug_raw_text=player.get('raw_text'),
                debug_roi=player.get('roi'),
                matched_by=player.get('matched_by'),
            ),
            opponent=RecognizedSide(
                name=opponent.get('name'),
                confidence=opponent.get('confidence', 0.0),
                source=RecognitionSource(opponent.get('source', 'mock')),
                debug_raw_text=opponent.get('raw_text'),
                debug_roi=opponent.get('roi'),
                matched_by=opponent.get('matched_by'),
            ),
            player_hp_current=player_hp_current,
            player_hp_max=player_hp_max,
            opponent_hp_percent=opponent_hp_percent,
            revealed_moves=revealed_moves,
            timestamp=frame.get('timestamp', ''),
        )
        self._last_result = result
        return result

    def get_current_state(self) -> RecognitionStatePayload:
        return self._last_result

    def override_side(self, side: str, name: str) -> RecognitionStatePayload:
        updated = self._last_result.model_copy(deep=True)
        manual_side = RecognizedSide(
            name=name,
            confidence=1.0,
            source=RecognitionSource.MANUAL,
            debug_raw_text=name,
            matched_by='manual',
        )
        if side == 'player':
            updated.player = manual_side
        elif side == 'opponent':
            updated.opponent = manual_side
        self._last_result = updated
        return self._last_result
