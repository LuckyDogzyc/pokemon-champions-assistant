from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSideRecognizer(ABC):
    @abstractmethod
    def recognize_side(self, frame: dict[str, Any], roi: dict[str, int], side: str) -> dict[str, Any]:
        raise NotImplementedError
