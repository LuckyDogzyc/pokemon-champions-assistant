from __future__ import annotations

import re
from typing import Callable, Any
from urllib.request import Request, urlopen


PIKALYTICS_MA1_POKEDEX_URL = "https://www.pikalytics.com/pokedex/championstournaments"
PIKALYTICS_MA1_FORMAT = "championstournaments-1760"


def _default_html_fetcher(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def _slugify_name(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def fetch_pikalytics_ma1_pokemon_list(
    *,
    html_fetcher: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    html = (html_fetcher or _default_html_fetcher)(PIKALYTICS_MA1_POKEDEX_URL)

    matched_names = re.findall(r'/pokedex/championstournaments/([A-Za-z0-9\-]+)\?l=en', html)
    unique_names = sorted({name for name in matched_names})
    pokemon = [
        {
            "slug": _slugify_name(name),
            "name": name,
        }
        for name in unique_names
    ]

    return {
        "files": {
            "pokemon.json": pokemon,
        },
        "meta": {
            "source": "pikalytics",
            "season": "MA1",
            "format": PIKALYTICS_MA1_FORMAT,
            "pokedex_url": PIKALYTICS_MA1_POKEDEX_URL,
            "pokemon_count": len(pokemon),
        },
    }
