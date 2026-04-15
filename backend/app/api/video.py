from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.video import (
    SelectVideoSourceRequest,
    SelectVideoSourceResponse,
    VideoSourcesResponse,
)
from app.services.capture_session import CaptureSessionService
from app.services.video_source_selection import VideoSourceSelectionStore
from app.services.video_source_service import VideoSourceService

router = APIRouter(prefix="/api/video", tags=["video"])
video_source_service = VideoSourceService()
selection_store = VideoSourceSelectionStore()
capture_session_service = CaptureSessionService()


def _mark_selected_sources(sources):
    selected_source_id = selection_store.get_selected_source_id()
    return [
        source.model_copy(update={"is_selected": source.id == selected_source_id})
        for source in sources
    ]


@router.get("/sources", response_model=VideoSourcesResponse)
def list_video_sources() -> VideoSourcesResponse:
    sources = video_source_service.list_sources()
    return VideoSourcesResponse(sources=_mark_selected_sources(sources))


@router.post("/source/select", response_model=SelectVideoSourceResponse)
def select_video_source(
    payload: SelectVideoSourceRequest,
) -> SelectVideoSourceResponse:
    sources = video_source_service.list_sources()
    known_source_ids = {source.id for source in sources}
    if payload.source_id not in known_source_ids:
        raise HTTPException(status_code=404, detail="未找到指定输入源")

    selected_source_id = selection_store.set_selected_source_id(payload.source_id)
    return SelectVideoSourceResponse(selected_source_id=selected_source_id)


@router.post("/session/start")
def start_capture_session() -> dict:
    source_id = selection_store.get_selected_source_id()
    return capture_session_service.start(source_id)


@router.post("/session/stop")
def stop_capture_session() -> dict:
    return capture_session_service.stop()


@router.get("/session/current")
def get_capture_session_state() -> dict:
    return capture_session_service.poll()
