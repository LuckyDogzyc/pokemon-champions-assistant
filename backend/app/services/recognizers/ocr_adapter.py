from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class OcrAdapter(ABC):
    @abstractmethod
    def read_text(self, frame: dict[str, Any], roi: dict[str, int]) -> list[dict[str, Any]]:
        raise NotImplementedError
