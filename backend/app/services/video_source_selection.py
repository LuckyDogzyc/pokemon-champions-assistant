from __future__ import annotations

from typing import Any

from app.core.settings import get_settings


class VideoSourceSelectionStore:
    def __init__(self, default_source_id: str | None = None) -> None:
        self._selected_source_id = default_source_id or get_settings().video_source
        self._selected_source: dict[str, Any] | None = None

    def get_selected_source_id(self) -> str:
        return self._selected_source_id

    def get_selected_source(self) -> dict[str, Any] | None:
        return self._selected_source

    def set_selected_source_id(self, source_id: str) -> str:
        self._selected_source_id = source_id
        self._selected_source = None
        return self._selected_source_id

    def set_selected_source(self, source: dict[str, Any]) -> str:
        self._selected_source = dict(source)
        self._selected_source_id = str(source.get('id') or self._selected_source_id)
        return self._selected_source_id
