from __future__ import annotations

from pydantic import BaseModel


class PokemonProfile(BaseModel):
    id: str
    name_zh: str
    name_en: str | None = None
    types: list[str]
    base_stats: dict[str, int] | None = None


class PokemonLookupResult(BaseModel):
    found: bool
    query: str
    canonical_name: str | None = None
    pokemon_id: str | None = None
    match_type: str = "none"
    score: float = 0.0
    pokemon: PokemonProfile | None = None


class PokemonSearchResponse(BaseModel):
    query: str
    results: list[PokemonLookupResult]
