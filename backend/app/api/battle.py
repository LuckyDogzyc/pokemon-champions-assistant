from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.battle_session import BattleSession
from app.schemas.battle_state import BattleState, BattleStateUpdateRequest
from app.services.battle_session_store import BattleSessionStore
from app.services.battle_state_store import BattleStateStore

router = APIRouter(prefix="/api/battle", tags=["battle"])
battle_session_router = APIRouter(prefix="/api/battle-session", tags=["battle-session"])
logger = logging.getLogger(__name__)


class BattleSessionManualOverrideRequest(BaseModel):
    side: str
    name: str


def _get_store() -> BattleStateStore:
    from app.api.recognition import battle_state_store
    return battle_state_store


def _get_session_store() -> BattleSessionStore:
    from app.api.recognition import battle_session_store
    return battle_session_store


@router.get("/state", response_model=BattleState)
def get_battle_state() -> BattleState:
    """Return the current tracked battle state."""
    return _get_store().state


@router.get("/session", response_model=BattleSession)
def get_battle_session() -> BattleSession:
    """Return the current battle session (per-match JSON data model)."""
    return _get_session_store().get_session()


@router.post("/reset", response_model=BattleState)
def reset_battle_state() -> BattleState:
    """Reset the battle state (start a new battle)."""
    return _get_store().reset()


@router.post("/update", response_model=BattleState)
def manual_update(payload: BattleStateUpdateRequest) -> BattleState:
    """Apply a manual update to the battle state."""
    return _get_store().manual_update(payload.field, payload.value)


@battle_session_router.get("/status", response_model=BattleSession)
def get_battle_session_status() -> BattleSession:
    """Compatibility endpoint for the PRD BattleSession status path."""
    return _get_session_store().get_session()


@battle_session_router.post("/manual-override", response_model=BattleSession)
def manual_override_battle_session(payload: BattleSessionManualOverrideRequest) -> BattleSession:
    """Apply a manual active Pokémon override and return the updated BattleSession."""
    from app.api import recognition as recognition_api

    state = recognition_api.recognition_pipeline.override_side(payload.side, payload.name)
    battle_state = recognition_api.battle_state_store.update_from_recognition(state)
    recognition_api.battle_session_store.sync_from_recognition(state)
    recognition_api.battle_session_store.append_log_batch(battle_state.move_log)
    return recognition_api.battle_session_store.get_session()
