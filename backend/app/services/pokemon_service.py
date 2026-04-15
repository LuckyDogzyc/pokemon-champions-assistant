from __future__ import annotations

from app.schemas.pokemon import PokemonLookupResult, PokemonProfile
from app.services.data_loader import load_pokemon_index
from app.services.name_matcher import NameMatcher


class PokemonService:
    def __init__(self, matcher: NameMatcher | None = None) -> None:
        self._matcher = matcher or NameMatcher()
        self._pokemon_by_id = {
            entry["id"]: PokemonProfile.model_validate(entry)
            for entry in load_pokemon_index()
        }

    def search(self, query: str) -> list[PokemonLookupResult]:
        match = self._matcher.match(query)
        if not match.found or match.pokemon_id is None:
            return []

        pokemon = self._pokemon_by_id[match.pokemon_id]
        return [
            PokemonLookupResult(
                found=True,
                query=match.query,
                canonical_name=match.canonical_name,
                pokemon_id=match.pokemon_id,
                match_type=match.match_type,
                score=match.score,
                pokemon=pokemon,
            )
        ]

    def get_by_query(self, query: str) -> PokemonLookupResult | None:
        results = self.search(query)
        if not results:
            return None
        return results[0]
