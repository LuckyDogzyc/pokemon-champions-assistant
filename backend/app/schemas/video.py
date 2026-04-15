from __future__ import annotations

from pydantic import BaseModel, Field


class VideoSource(BaseModel):
    id: str
    label: str
    backend: str
    is_capture_card_candidate: bool = False
    is_selected: bool = False


class VideoSourcesResponse(BaseModel):
    sources: list[VideoSource] = Field(default_factory=list)


class SelectVideoSourceRequest(BaseModel):
    source_id: str


class SelectVideoSourceResponse(BaseModel):
    selected_source_id: str
