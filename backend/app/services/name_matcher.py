from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.data_loader import load_aliases, load_pokemon_index

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback for environments missing the optional wheel
    fuzz = None


MIN_FUZZY_SCORE = 60.0


@dataclass(frozen=True)
class MatchResult:
    found: bool
    query: str
    canonical_name: str | None = None
    pokemon_id: str | None = None
    match_type: str = "none"
    score: float = 0.0


class NameMatcher:
    def __init__(self, min_fuzzy_score: float = MIN_FUZZY_SCORE) -> None:
        pokemon_index = load_pokemon_index()
        aliases = load_aliases()

        self._min_fuzzy_score = min_fuzzy_score
        self._pokemon_by_id = {entry["id"]: entry for entry in pokemon_index}
        self._canonical_by_normalized_name = {
            self._normalize(entry["name_zh"]): entry for entry in pokemon_index
        }
        self._alias_to_id = {
            self._normalize(alias): pokemon_id for alias, pokemon_id in aliases.items()
        }

    def match(self, raw_query: str) -> MatchResult:
        query = raw_query.strip()
        if not query:
            return MatchResult(found=False, query=raw_query)

        normalized_query = self._normalize(query)
        exact_entry = self._canonical_by_normalized_name.get(normalized_query)
        if exact_entry is not None:
            return MatchResult(
                found=True,
                query=query,
                canonical_name=exact_entry["name_zh"],
                pokemon_id=exact_entry["id"],
                match_type="exact",
                score=100.0,
            )

        alias_target_id = self._alias_to_id.get(normalized_query)
        if alias_target_id is not None:
            alias_entry = self._pokemon_by_id[alias_target_id]
            return MatchResult(
                found=True,
                query=query,
                canonical_name=alias_entry["name_zh"],
                pokemon_id=alias_entry["id"],
                match_type="alias",
                score=100.0,
            )

        candidate = self._best_fuzzy_match(normalized_query)
        if candidate is None:
            return MatchResult(found=False, query=query)

        pokemon_id, score = candidate
        pokemon_entry = self._pokemon_by_id[pokemon_id]
        return MatchResult(
            found=True,
            query=query,
            canonical_name=pokemon_entry["name_zh"],
            pokemon_id=pokemon_entry["id"],
            match_type="fuzzy",
            score=score,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(value.strip().lower().split())

    def _best_fuzzy_match(self, normalized_query: str) -> tuple[str, float] | None:
        best_match: tuple[str, float, float] | None = None
        for normalized_name, entry in self._canonical_by_normalized_name.items():
            score = self._similarity(normalized_query, normalized_name)
            if score < self._min_fuzzy_score:
                continue
            adjusted_score = score - (abs(len(normalized_query) - len(normalized_name)) * 15)
            if best_match is None or adjusted_score > best_match[2] or (
                adjusted_score == best_match[2] and score > best_match[1]
            ):
                best_match = (entry["id"], score, adjusted_score)

        if best_match is None:
            return None
        return best_match[0], best_match[1]

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        if fuzz is not None:
            return float(fuzz.ratio(left, right))
        return SequenceMatcher(a=left, b=right).ratio() * 100.0
