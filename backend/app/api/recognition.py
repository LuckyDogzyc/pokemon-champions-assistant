from __future__ import annotations

from fastapi import APIRouter

from app.api.video import capture_session_service, selection_store
from app.schemas.recognition import RecognitionStatePayload
from app.services.recognition_pipeline import RecognitionPipeline

router = APIRouter(prefix="/api/recognition", tags=["recognition"])
recognition_pipeline = RecognitionPipeline()


def _enrich_state(state: RecognitionStatePayload, input_source: str) -> dict:
    payload = state.model_dump(mode="json")
    payload["input_source"] = input_source
    return payload


@router.post("/session/start")
def start_recognition_session() -> dict:
    source_id = selection_store.get_selected_source_id()
    capture_state = capture_session_service.start(source_id)
    latest_frame = capture_state.get("latest_frame") or {}
    current_state = recognition_pipeline.recognize(latest_frame)
    return {
        "running": capture_state.get("running", False),
        "input_source": capture_state.get("source_id"),
        "current_state": _enrich_state(current_state, capture_state.get("source_id")),
    }


@router.get("/current")
def get_current_recognition() -> dict:
    capture_state = capture_session_service.poll()
    latest_frame = capture_state.get("latest_frame") or {}
    if latest_frame:
        state = recognition_pipeline.recognize(latest_frame)
    else:
        state = recognition_pipeline.get_current_state()
    return _enrich_state(state, capture_state.get("source_id"))
