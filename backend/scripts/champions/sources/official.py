from __future__ import annotations

import ast
import re
from typing import Callable, Any
from urllib.request import Request, urlopen

try:
    from app.services.data_loader import load_aliases, load_pokemon_index
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from app.services.data_loader import load_aliases, load_pokemon_index


OFFICIAL_MA1_EVENT_ID = "rs177501629259kmzbny"
OFFICIAL_MA1_POKEMON_URL = (
    "https://web-view.app.pokemonchampions.jp/battle/pages/events/"
    f"{OFFICIAL_MA1_EVENT_ID}/ja/pokemon.html"
)


def _default_html_fetcher(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def _parse_name_parts(name_ja: str) -> tuple[str, str | None, bool]:
    match = re.match(r"^(.*?)\s*\((.*?)\)$", name_ja.strip())
    if match is None:
        normalized = name_ja.strip()
        return normalized, None, False
    base_name = match.group(1).strip()
    form_name = match.group(2).strip()
    return base_name, form_name, True


def _build_index_lookup(pokemon_index: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(entry["id"]).zfill(3): dict(entry)
        for entry in pokemon_index
        if isinstance(entry, dict) and entry.get("id")
    }


def _build_alias_keys(aliases_zh: dict[str, str], pokemon_id: str) -> list[str]:
    keys = sorted(alias for alias, target_id in aliases_zh.items() if str(target_id).zfill(3) == pokemon_id)
    return keys


def _normalize_official_entry(
    code: str,
    name_ja: str,
    *,
    pokemon_index_lookup: dict[str, dict[str, Any]],
    aliases_zh: dict[str, str],
) -> dict[str, Any]:
    dex_no, form_no = str(code).split("-", 1)
    pokemon_id = dex_no[-3:]
    base_name, form_name, is_form = _parse_name_parts(str(name_ja))
    pokemon_seed = pokemon_index_lookup.get(pokemon_id, {})
    alias_keys = _build_alias_keys(aliases_zh, pokemon_id)
    match_key = str(pokemon_seed.get("name_zh") or base_name)
    if match_key and match_key not in alias_keys:
        alias_keys = sorted({match_key, *alias_keys})
    return {
        "code": str(code),
        "dex_no": dex_no,
        "form_no": form_no,
        "slug": str(code),
        "name_ja": str(name_ja),
        "base_name_ja": base_name,
        "form_name_ja": form_name,
        "is_form": is_form,
        "pokemon_id": pokemon_id,
        "name_zh": pokemon_seed.get("name_zh"),
        "name_en": pokemon_seed.get("name_en"),
        "match_key": match_key,
        "alias_keys": alias_keys,
    }


def fetch_official_ma1_pokemon_list(
    *,
    html_fetcher: Callable[[str], str] | None = None,
    pokemon_index: list[dict[str, Any]] | None = None,
    aliases_zh: dict[str, str] | None = None,
) -> dict[str, Any]:
    html = (html_fetcher or _default_html_fetcher)(OFFICIAL_MA1_POKEMON_URL)
    match = re.search(r"const pokemons = (\[.*?\]);", html, re.S)
    if match is None:
        raise ValueError("官方 MA1 页面中未找到 pokemons 列表")

    pokemon_index_lookup = _build_index_lookup(pokemon_index or load_pokemon_index())
    aliases = dict(aliases_zh or load_aliases())
    raw_pokemons = ast.literal_eval(match.group(1))
    seen_codes: set[str] = set()
    pokemon: list[dict[str, Any]] = []
    for code, enabled, name_ja in raw_pokemons:
        if not enabled:
            continue
        if code in seen_codes:
            continue
        seen_codes.add(code)
        pokemon.append(
            _normalize_official_entry(
                str(code),
                str(name_ja),
                pokemon_index_lookup=pokemon_index_lookup,
                aliases_zh=aliases,
            )
        )

    return {
        "files": {
            "pokemon.json": pokemon,
        },
        "meta": {
            "source": "pokemonchampions-official",
            "season": "MA1",
            "event_id": OFFICIAL_MA1_EVENT_ID,
            "pokemon_url": OFFICIAL_MA1_POKEMON_URL,
            "pokemon_count": len(pokemon),
        },
    }
