from __future__ import annotations

from copy import deepcopy
from typing import Any


class FrameStore:
    def __init__(self) -> None:
        self._latest_frame: dict[str, Any] | None = None

    def set_latest_frame(self, frame_metadata: dict[str, Any]) -> None:
        self._latest_frame = deepcopy(frame_metadata)

    def get_latest_frame(self) -> dict[str, Any] | None:
        if self._latest_frame is None:
            return None
        return deepcopy(self._latest_frame)
