from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api import video as video_api
from app.schemas.recognition import (
    ManualOverrideRequest,
    RecognitionStatePayload,
)
from app.services.battle_state_store import BattleStateStore
from app.services.frame_store import FrameStore
from app.services.recognition_pipeline import build_phase_snapshot, build_roi_payloads
from app.services.roi_capture import enrich_roi_payloads_with_crops
from app.services.recognition_runtime import (
    RecognizeScheduler,
    create_recognition_runtime,
)

router = APIRouter(prefix='/api/recognition', tags=['recognition'])
logger = logging.getLogger(__name__)
recognition_runtime = create_recognition_runtime()
recognition_pipeline = recognition_runtime.pipeline
battle_state_store = BattleStateStore()
frame_store = FrameStore()
recognize_scheduler = RecognizeScheduler(
    pipeline=recognition_pipeline,
    frame_store=frame_store,
    battle_state_store=battle_state_store,
    interval_seconds=1.0,
)

# Share the same frame_store with the capture service
video_api.capture_session_service._frame_store = frame_store


def _build_capture_guidance(latest_frame: dict | None) -> dict[str, str | None]:
    error_detail = str((latest_frame or {}).get('error_detail') or '')
    if not error_detail:
        return {
            'capture_help_text': None,
            'capture_suggested_source_id': None,
            'capture_suggested_source_label': None,
        }

    normalized_error = error_detail.lower()
    if 'could not run graph' not in normalized_error and 'device already in use' not in normalized_error:
        return {
            'capture_help_text': None,
            'capture_suggested_source_id': None,
            'capture_suggested_source_label': None,
        }

    suggested_source = None
    for source in video_api.video_source_service.list_sources():
        label = str(source.label or '')
        if 'obs virtual camera' in label.lower():
            suggested_source = source
            break

    if suggested_source is None:
        return {
            'capture_help_text': '当前采集卡可能正被其他程序占用。若需要保持 OBS 开启，请在 OBS 中启动虚拟摄像头后改选 OBS Virtual Camera。',
            'capture_suggested_source_id': None,
            'capture_suggested_source_label': None,
        }

    return {
        'capture_help_text': '当前采集卡可能正被其他程序占用。若需要保持 OBS 开启，请在 OBS 中启动虚拟摄像头并切换到 OBS Virtual Camera。',
        'capture_suggested_source_id': suggested_source.id,
        'capture_suggested_source_label': suggested_source.label,
    }


def _build_ocr_debug() -> dict[str, str | None]:
    return {
        'ocr_provider': recognition_runtime.active_provider,
        'ocr_warning': recognition_runtime.warning,
    }


def _build_frame_variants_debug(latest_frame: dict | None) -> dict[str, dict[str, str | int | None]]:
    base_frame = latest_frame or {}
    frame_variants = dict(base_frame.get('frame_variants') or {})

    def _variant_debug(name: str) -> dict[str, str | int | None]:
        variant = frame_variants.get(name)
        if isinstance(variant, dict):
            return {
                'source': f'capture.frame_variants.{name}',
                'width': variant.get('width'),
                'height': variant.get('height'),
                'preview_image_data_url': variant.get('preview_image_data_url'),
            }
        return {
            'source': 'base-frame-fallback',
            'width': base_frame.get('width'),
            'height': base_frame.get('height'),
            'preview_image_data_url': base_frame.get('preview_image_data_url'),
        }

    return {
        'phase_frame': _variant_debug('phase_frame'),
        'roi_source_frame': _variant_debug('roi_source_frame'),
    }


def _resolve_roi_source_frame(latest_frame: dict | None) -> dict:
    base_frame = latest_frame or {}
    roi_source_frame = dict((base_frame.get('frame_variants') or {}).get('roi_source_frame') or {})
    if roi_source_frame:
        roi_source_frame.setdefault('width', base_frame.get('width'))
        roi_source_frame.setdefault('height', base_frame.get('height'))
        roi_source_frame.setdefault('preview_image_data_url', base_frame.get('preview_image_data_url'))
        roi_source_frame.setdefault('layout_variant', base_frame.get('layout_variant'))
        roi_source_frame.setdefault('layout_variant_hint', base_frame.get('layout_variant_hint'))
        return roi_source_frame
    return dict(base_frame)


def _build_fallback_roi_payloads(latest_frame: dict | None, *, phase: str, layout_variant: str | None) -> dict:
    roi_source_frame = _resolve_roi_source_frame(latest_frame)
    roi_payloads = build_roi_payloads(roi_source_frame, phase=phase, layout_variant=layout_variant)
    return enrich_roi_payloads_with_crops(roi_source_frame, roi_payloads)


def _enrich_existing_roi_payloads_with_crops(latest_frame: dict | None, roi_payloads: dict) -> dict:
    roi_source_frame = _resolve_roi_source_frame(latest_frame)
    enriched_payloads = enrich_roi_payloads_with_crops(roi_source_frame, roi_payloads)
    merged_payloads: dict = {}
    crop_keys = ('pixel_box', 'preview_image_data_url', 'crop_width', 'crop_height')
    for name, original_payload in roi_payloads.items():
        merged_payload = dict(enriched_payloads.get(name, original_payload))
        for key in crop_keys:
            if original_payload.get(key) not in (None, '', {}):
                merged_payload[key] = original_payload[key]
        merged_payloads[name] = merged_payload
    return merged_payloads


def _build_phase_first_payload(state_payload: dict, latest_frame: dict | None) -> dict:
    layout_variant = state_payload.get('layout_variant') or (latest_frame or {}).get('layout_variant') or (latest_frame or {}).get('layout_variant_hint')
    phase = str(state_payload.get('current_phase') or 'unknown')
    if not layout_variant and phase == 'battle' and (latest_frame or {}).get('preview_image_data_url'):
        layout_variant = 'battle_move_menu_open'
    phase_evidence = list(state_payload.get('phase_evidence') or [])
    if not phase_evidence:
        ui = (latest_frame or {}).get('ui') or {}
        phase_evidence = [key for key, value in ui.items() if value]

    if state_payload.get('phase_snapshot'):
        phase_snapshot = state_payload['phase_snapshot']
    else:
        phase_snapshot = build_phase_snapshot(
            phase=phase,
            confidence=1.0 if phase_evidence else 0.0,
            evidence=phase_evidence,
        )

    if state_payload.get('roi_payloads'):
        roi_payloads = _enrich_existing_roi_payloads_with_crops(latest_frame, state_payload['roi_payloads'])
    else:
        roi_payloads = _build_fallback_roi_payloads(latest_frame, phase=phase, layout_variant=layout_variant)

    return {
        'phase_snapshot': phase_snapshot,
        'roi_payloads': roi_payloads,
        'frame_variants_debug': _build_frame_variants_debug(latest_frame),
    }


def _enrich_state(
    state: RecognitionStatePayload,
    input_source: str,
    latest_frame: dict | None = None,
    *,
    recognition_error: str | None = None,
    recognition_error_detail: str | None = None,
) -> dict:
    payload = state.model_dump(mode='json')
    payload['input_source'] = input_source
    payload['preview_image_data_url'] = (latest_frame or {}).get('preview_image_data_url')
    payload['capture_error'] = (latest_frame or {}).get('error')
    payload['capture_error_detail'] = (latest_frame or {}).get('error_detail')
    payload['capture_method'] = (latest_frame or {}).get('capture_method')
    payload['capture_backend'] = (latest_frame or {}).get('capture_backend')
    payload['recognition_error'] = recognition_error
    payload['recognition_error_detail'] = recognition_error_detail
    payload.update(_build_phase_first_payload(payload, latest_frame))
    payload.update(_build_capture_guidance(latest_frame))
    payload.update(_build_ocr_debug())
    payload['battle_state'] = battle_state_store.state.model_dump(mode='json')

    # Signal to frontend if battle data was just reset (either by
    # settlement detection or manual /reset call)
    payload['battle_reset'] = battle_state_store.was_just_reset()

    # Inject base stats for active mons so frontend can show speed comparison etc.
    from app.services.data_loader import load_base_stats as _load_base_stats
    _all_stats = _load_base_stats()
    _p_stats = _all_stats.get(payload.get('player', {}).get('matched_pokemon_id') or '')
    _o_stats = _all_stats.get(payload.get('opponent', {}).get('matched_pokemon_id') or '')
    if _p_stats:
        payload['player_base_stats'] = _p_stats
    if _o_stats:
        payload['opponent_base_stats'] = _o_stats
    return payload


@router.post('/session/start')
def start_recognition_session() -> dict:
    capture_state = video_api.capture_session_service.start(video_api._resolve_selected_source())
    # Start the background recognition scheduler
    recognize_scheduler.start()

    # Get the initial result — run one recognition cycle synchronously
    # so the first poll has data.  Use the just-captured frame from the
    # capture session result.
    capture_latest = capture_state.get('latest_frame') or {}
    # Ensure it's also in our shared frame_store
    if capture_latest and frame_store.get_latest_frame() is None:
        frame_store.set_latest_frame(capture_latest)

    latest_frame = frame_store.get_latest_frame() or capture_latest
    try:
        if latest_frame:
            current_state = recognition_pipeline.recognize(latest_frame)
            recognition_pipeline.set_current_state(current_state)
            battle_state_store.update_from_recognition(current_state)
    except Exception as exc:  # pragma: no cover
        logger.exception('Initial recognition failed')
        current_state = recognition_pipeline.get_current_state()
    else:
        current_state = recognition_pipeline.get_current_state()

    return {
        'running': capture_state.get('running', False),
        'input_source': capture_state.get('source_id'),
        'current_state': _enrich_state(
            current_state,
            capture_state.get('source_id'),
            latest_frame or frame_store.get_latest_frame(),
        ),
    }


@router.post('/session/stop')
def stop_recognition_session() -> dict:
    recognize_scheduler.stop()
    capture_state = video_api.capture_session_service.stop()
    return {
        'running': capture_state.get('running', False),
        'input_source': capture_state.get('source_id'),
    }


@router.get('/current')
def get_current_recognition() -> dict:
    """Return the latest recognition result without triggering capture or OCR.

    Capture runs on a background 1s thread (CaptureSessionService).
    Recognition runs on a background 1s thread (RecognizeScheduler).
    This endpoint just reads the latest shared state.
    """
    state = recognition_pipeline.get_current_state()
    return _enrich_state(
        state,
        video_api.selection_store.get_selected_source_id(),
        frame_store.get_latest_frame(),
    )


@router.post('/session/reset')
def reset_recognition_session() -> dict:
    """Reset all battle state data (teams, active mons, battle log, etc.)

    Capture and recognition continue running — only the accumulated
    battle state is cleared.  The UI can then re-populate from fresh
    recognition results.
    """
    battle_state_store.reset()
    import copy
    fresh_state = recognition_pipeline.get_current_state()
    fresh_state = copy.deepcopy(fresh_state)
    # Reset team-related fields so the frontend gets a clean slate
    fresh_state.player_team_slots = []
    fresh_state.opponent_team_slots = []
    if hasattr(fresh_state, 'team_preview'):
        fresh_state.team_preview = None
    recognition_pipeline.set_current_state(fresh_state)
    return {
        'reset': True,
        'current_state': _enrich_state(
            fresh_state,
            video_api.selection_store.get_selected_source_id(),
            frame_store.get_latest_frame(),
        ),
    }


@router.post('/override')
def override_recognition(payload: ManualOverrideRequest) -> dict:
    state = recognition_pipeline.override_side(payload.side.value, payload.name)
    return _enrich_state(state, video_api.selection_store.get_selected_source_id())
