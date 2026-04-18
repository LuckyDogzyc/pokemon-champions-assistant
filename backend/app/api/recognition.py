from __future__ import annotations

from fastapi import APIRouter

from app.api.video import _resolve_selected_source, capture_session_service, selection_store
from app.schemas.phase import BattlePhase
from app.schemas.recognition import (
    ManualOverrideRequest,
    RecognitionStatePayload,
)
from app.services.recognition_pipeline import RecognitionPipeline

router = APIRouter(prefix='/api/recognition', tags=['recognition'])
recognition_pipeline = RecognitionPipeline()


def _enrich_state(state: RecognitionStatePayload, input_source: str, latest_frame: dict | None = None) -> dict:
    payload = state.model_dump(mode='json')
    payload['input_source'] = input_source
    payload['preview_image_data_url'] = (latest_frame or {}).get('preview_image_data_url')
    payload['capture_error'] = (latest_frame or {}).get('error')
    payload['capture_error_detail'] = (latest_frame or {}).get('error_detail')
    payload['capture_method'] = (latest_frame or {}).get('capture_method')
    payload['capture_backend'] = (latest_frame or {}).get('capture_backend')
    return payload


@router.post('/session/start')
def start_recognition_session() -> dict:
    capture_state = capture_session_service.start(_resolve_selected_source())
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
    capture_state = capture_session_service.poll()
    latest_frame = capture_state.get('latest_frame') or {}
    if latest_frame:
        state = recognition_pipeline.recognize(latest_frame)
    else:
        state = recognition_pipeline.get_current_state()
    return _enrich_state(state, capture_state.get('source_id'), capture_state.get('latest_frame'))


@router.post('/override')
def override_recognition(payload: ManualOverrideRequest) -> dict:
    state = recognition_pipeline.override_side(payload.side.value, payload.name)
    return _enrich_state(state, selection_store.get_selected_source_id())
