from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.types import CombinedTypeMatchupsResponse, CombinedTypesRequest, TypeMatchupsResponse
from app.services.type_service import TypeService

router = APIRouter(prefix="/api/type", tags=["types"])
service = TypeService()


@router.get("/{type_name}/matchups", response_model=TypeMatchupsResponse)
def get_type_matchups(type_name: str) -> TypeMatchupsResponse:
    try:
        return service.get_matchups(type_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/combined-matchups", response_model=CombinedTypeMatchupsResponse)
def get_combined_matchups(payload: CombinedTypesRequest) -> CombinedTypeMatchupsResponse:
    try:
        return service.get_combined_matchups(payload.types)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
