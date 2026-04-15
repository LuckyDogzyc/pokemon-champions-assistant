from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.pokemon import PokemonLookupResult, PokemonSearchResponse
from app.services.pokemon_service import PokemonService

router = APIRouter(prefix="/api/pokemon", tags=["pokemon"])
service = PokemonService()


@router.get("/search", response_model=PokemonSearchResponse)
def search_pokemon(q: str = Query(..., min_length=1)) -> PokemonSearchResponse:
    return PokemonSearchResponse(query=q, results=service.search(q))


@router.get("/{query}", response_model=PokemonLookupResult)
def get_pokemon(query: str) -> PokemonLookupResult:
    result = service.get_by_query(query)
    if result is None:
        raise HTTPException(status_code=404, detail="未找到匹配的宝可梦")
    return result
