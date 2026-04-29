from __future__ import annotations

import logging

from fastapi import APIRouter

from app.schemas.battle_state import BattleState, BattleStateUpdateRequest
from app.services.battle_state_store import BattleStateStore

router = APIRouter(prefix="/api/battle", tags=["battle"])
logger = logging.getLogger(__name__)

# Shared store instance — imported from recognition module to stay in sync
def _get_store() -> BattleStateStore:
    from app.api.recognition import battle_state_store
    return battle_state_store


@router.get("/state", response_model=BattleState)
def get_battle_state() -> BattleState:
    """Return the current tracked battle state."""
    return _get_store().state


@router.post("/reset", response_model=BattleState)
def reset_battle_state() -> BattleState:
    """Reset the battle state (start a new battle)."""
    return _get_store().reset()


@router.post("/update", response_model=BattleState)
def manual_update(payload: BattleStateUpdateRequest) -> BattleState:
    """Apply a manual update to the battle state."""
    return _get_store().manual_update(payload.field, payload.value)
