from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.video import (
    SelectVideoSourceRequest,
    SelectVideoSourceResponse,
    VideoSourcesResponse,
)
from app.services.capture_session import (
    CaptureSessionService,
    black_preview_image_data_url,
)
from app.services.video_source_selection import VideoSourceSelectionStore
from app.services.video_source_service import VideoSourceService

router = APIRouter(prefix='/api/video', tags=['video'])
video_source_service = VideoSourceService()
selection_store = VideoSourceSelectionStore()
capture_session_service = CaptureSessionService()


def _pick_preferred_source(sources):
    selected_source = selection_store.get_selected_source()
    if selected_source is not None:
        selected_id = str(selected_source.get('id'))
        for source in sources:
            if source.id == selected_id:
                return source

    selected_source_id = selection_store.get_selected_source_id()
    for source in sources:
        if source.id == selected_source_id:
            return source

    for source in sources:
        if 'obs virtual camera' in source.label.lower():
            return source

    for source in sources:
        if getattr(source, 'device_kind', None) == 'virtual':
            return source

    for source in sources:
        if source.is_capture_card_candidate:
            return source

    return sources[0] if sources else None


def _mark_selected_sources(sources):
    preferred_source = _pick_preferred_source(sources)
    if preferred_source is not None:
        selection_store.set_selected_source(preferred_source.model_dump(mode='json'))
        selected_source_id = preferred_source.id
    else:
        selected_source_id = selection_store.get_selected_source_id()
    return [
        source.model_copy(update={'is_selected': source.id == selected_source_id})
        for source in sources
    ]


def _resolve_selected_source():
    sources = video_source_service.list_sources()
    preferred_source = _pick_preferred_source(sources)
    if preferred_source is not None:
        resolved = preferred_source.model_dump(mode='json')
        selection_store.set_selected_source(resolved)
        return resolved

    selected_source_id = selection_store.get_selected_source_id()
    return {'id': selected_source_id, 'backend': 'opencv', 'capture_selector': selected_source_id}


@router.get('/sources', response_model=VideoSourcesResponse)
def list_video_sources() -> VideoSourcesResponse:
    sources = video_source_service.list_sources()
    return VideoSourcesResponse(sources=_mark_selected_sources(sources))


@router.post('/source/select', response_model=SelectVideoSourceResponse)
def select_video_source(
    payload: SelectVideoSourceRequest,
) -> SelectVideoSourceResponse:
    sources = video_source_service.list_sources()
    known_source_ids = {source.id for source in sources}
    if payload.source_id not in known_source_ids:
        raise HTTPException(status_code=404, detail='未找到指定输入源')

    selected_source = next(source for source in sources if source.id == payload.source_id)
    selected_source_id = selection_store.set_selected_source(selected_source.model_dump(mode='json'))
    return SelectVideoSourceResponse(selected_source_id=selected_source_id)


@router.get('/latest-frame')
def get_latest_frame() -> dict:
    """Lightweight endpoint: returns only the latest captured frame without running OCR.
    
    Used by the main game screen to refresh at full capture rate (2s),
    independent of the slower OCR pipeline (~4s including OCR time).
    """
    capture_state = video_api.capture_session_service.poll()
    latest_frame = capture_state.get('latest_frame') or {}
    frame_variants = latest_frame.get('frame_variants') or {}
    roi_source_frame = frame_variants.get('roi_source_frame') or {}
    
    preview = (
        roi_source_frame.get('preview_image_data_url')
        or latest_frame.get('preview_image_data_url')
        or black_preview_image_data_url()
    )
    
    return {
        'preview_image_data_url': preview,
        'width': roi_source_frame.get('width') or latest_frame.get('width'),
        'height': roi_source_frame.get('height') or latest_frame.get('height'),
        'capture_error': latest_frame.get('error'),
        'capture_error_detail': latest_frame.get('error_detail'),
        'input_source': capture_state.get('source_id'),
    }


@router.post('/session/start')
def start_capture_session() -> dict:
    return capture_session_service.start(_resolve_selected_source())


@router.post('/session/stop')
def stop_capture_session() -> dict:
    return capture_session_service.stop()


@router.get('/session/current')
def get_capture_session_state() -> dict:
    return capture_session_service.poll()
