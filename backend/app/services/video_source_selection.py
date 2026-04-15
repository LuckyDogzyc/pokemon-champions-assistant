from __future__ import annotations

from app.core.settings import get_settings


class VideoSourceSelectionStore:
    def __init__(self, default_source_id: str | None = None) -> None:
        self._selected_source_id = default_source_id or get_settings().video_source

    def get_selected_source_id(self) -> str:
        return self._selected_source_id

    def set_selected_source_id(self, source_id: str) -> str:
        self._selected_source_id = source_id
        return self._selected_source_id
