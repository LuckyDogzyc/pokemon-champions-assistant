from __future__ import annotations

from app.schemas.phase import BattlePhase
from app.schemas.recognition import (
    RecognitionSource,
    RecognitionStatePayload,
    RecognizedSide,
    TeamPreviewState,
)
from app.services.layout_anchors import get_battle_name_anchors, get_layout_anchors
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
        for key in ('instruction_banner', 'player_team_list', 'opponent_team_list'):
            if key not in anchors:
                continue
            payloads[key] = {
                **anchors[key],
                'role': 'phase-detection' if key == 'instruction_banner' else key,
                'source': 'phase-frame' if key == 'instruction_banner' else 'roi-source-frame',
                'layout_variant': layout_variant,
            }
        return payloads

    if phase == BattlePhase.BATTLE:
        battle_anchors = get_battle_name_anchors({**frame, 'layout_variant': layout_variant, 'layout_variant_hint': layout_variant})
        payloads = {
            'player_name': {
                **battle_anchors['player'],
                'role': 'battle-player-name',
                'source': 'roi-source-frame',
                'layout_variant': layout_variant,
            },
            'opponent_name': {
                **battle_anchors['opponent'],
                'role': 'battle-opponent-name',
                'source': 'roi-source-frame',
                'layout_variant': layout_variant,
            },
        }
        for key, role in {
            'player_status_panel': 'battle-player-status-panel',
            'opponent_status_panel': 'battle-opponent-status-panel',
            'command_panel': 'battle-command-panel',
            'move_list': 'battle-move-list',
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
        phase_result = self._phase_detector.detect(frame)
        layout_variant = frame.get('layout_variant') or frame.get('layout_variant_hint')
        phase_snapshot = build_phase_snapshot(
            phase=str(phase_result.phase),
            confidence=float(phase_result.confidence),
            evidence=list(phase_result.evidence),
        )
        roi_payloads = self._enrich_roi_payloads(
            frame,
            build_roi_payloads(frame, phase=str(phase_result.phase), layout_variant=layout_variant),
        )

        if phase_result.phase == BattlePhase.TEAM_SELECT:
            annotation_target = frame.get('annotation_target', {})
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

        anchors = get_battle_name_anchors({**frame, 'layout_variant': layout_variant, 'layout_variant_hint': layout_variant})
        player = self._recognizer.recognize_side(frame, anchors['player'], 'player')
        opponent = self._recognizer.recognize_side(frame, anchors['opponent'], 'opponent')
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
