from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.pokemon import PokemonLookupResult, PokemonSearchResponse
from app.services.data_loader import load_base_stats, load_moves_index
from app.services.pokemon_service import PokemonService

router = APIRouter(prefix="/api/pokemon", tags=["pokemon"])
service = PokemonService()


@router.get("/search", response_model=PokemonSearchResponse)
def search_pokemon(q: str = Query(..., min_length=1)) -> PokemonSearchResponse:
    return PokemonSearchResponse(query=q, results=service.search(q))


@router.get("/moves")
def search_moves(q: str = Query("", min_length=0)) -> dict:
    """Search moves by name. Returns all moves if q is empty."""
    moves = load_moves_index()
    if not q:
        return {"moves": moves}
    q_lower = q.lower()
    matched = {
        mid: info for mid, info in moves.items()
        if q_lower in mid or q_lower in info.get("name", "").lower()
    }
    return {"moves": matched}


@router.get("/base-stats")
def get_base_stats() -> dict:
    """Return all base stats data."""
    return {"base_stats": load_base_stats()}


@router.get("/{query}", response_model=PokemonLookupResult)
def get_pokemon(query: str) -> PokemonLookupResult:
    result = service.get_by_query(query)
    if result is None:
        raise HTTPException(status_code=404, detail="未找到匹配的宝可梦")
    return result
