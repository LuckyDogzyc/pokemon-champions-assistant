from __future__ import annotations

from fastapi import APIRouter

from app.api import video as video_api
from app.schemas.recognition import (
    ManualOverrideRequest,
    RecognitionStatePayload,
)
from app.services.recognition_pipeline import RecognitionPipeline, build_phase_snapshot, build_roi_payloads

router = APIRouter(prefix='/api/recognition', tags=['recognition'])
recognition_pipeline = RecognitionPipeline()


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


def _build_phase_first_payload(state_payload: dict, latest_frame: dict | None) -> dict:
    layout_variant = state_payload.get('layout_variant') or (latest_frame or {}).get('layout_variant') or (latest_frame or {}).get('layout_variant_hint')
    phase = str(state_payload.get('current_phase') or 'unknown')
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
        roi_payloads = state_payload['roi_payloads']
    else:
        roi_payloads = build_roi_payloads(latest_frame or {}, phase=phase, layout_variant=layout_variant)

    return {
        'phase_snapshot': phase_snapshot,
        'roi_payloads': roi_payloads,
        'frame_variants_debug': _build_frame_variants_debug(latest_frame),
    }


def _enrich_state(state: RecognitionStatePayload, input_source: str, latest_frame: dict | None = None) -> dict:
    payload = state.model_dump(mode='json')
    payload['input_source'] = input_source
    payload['preview_image_data_url'] = (latest_frame or {}).get('preview_image_data_url')
    payload['capture_error'] = (latest_frame or {}).get('error')
    payload['capture_error_detail'] = (latest_frame or {}).get('error_detail')
    payload['capture_method'] = (latest_frame or {}).get('capture_method')
    payload['capture_backend'] = (latest_frame or {}).get('capture_backend')
    payload.update(_build_phase_first_payload(payload, latest_frame))
    payload.update(_build_capture_guidance(latest_frame))
    return payload


@router.post('/session/start')
def start_recognition_session() -> dict:
    capture_state = video_api.capture_session_service.start(video_api._resolve_selected_source())
    latest_frame = capture_state.get('latest_frame') or {}
    current_state = recognition_pipeline.recognize(latest_frame)
    return {
        'running': capture_state.get('running', False),
        'input_source': capture_state.get('source_id'),
        'current_state': _enrich_state(
            current_state,
            capture_state.get('source_id'),
            capture_state.get('latest_frame'),
        ),
    }


@router.get('/current')
def get_current_recognition() -> dict:
    capture_state = video_api.capture_session_service.poll()
    latest_frame = capture_state.get('latest_frame') or {}
    if latest_frame:
        state = recognition_pipeline.recognize(latest_frame)
    else:
        state = recognition_pipeline.get_current_state()
    return _enrich_state(state, capture_state.get('source_id'), capture_state.get('latest_frame'))


@router.post('/override')
def override_recognition(payload: ManualOverrideRequest) -> dict:
    state = recognition_pipeline.override_side(payload.side.value, payload.name)
    return _enrich_state(state, video_api.selection_store.get_selected_source_id())
