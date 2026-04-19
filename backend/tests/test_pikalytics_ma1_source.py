from __future__ import annotations

import json
from pathlib import Path


OFFICIAL_MA1_HTML = """
<!doctype html>
<html lang="ja">
<body>
  <main>
    <article>
      <div>
        <h1>参加できるポケモン</h1>
      </div>
      <div id="pokemons"></div>
    </article>
  </main>
  <script>
    const pokemons = [["0003-000",1,"フシギバナ"],["0006-000",1,"リザードン"],["0006-000",1,"リザードン"],["0026-001",1,"ライチュウ (アローラのすがた)"]];
  </script>
</body>
</html>
""".strip()


POKEMON_ZH_INDEX = [
    {"id": "003", "name_zh": "妙蛙花", "name_en": "Venusaur", "types": ["草", "毒"]},
    {"id": "006", "name_zh": "喷火龙", "name_en": "Charizard", "types": ["火", "飞行"]},
    {"id": "026", "name_zh": "雷丘", "name_en": "Raichu", "types": ["电"]},
]


ALIASES_ZH = {
    "妙蛙花": "003",
    "喷火龙": "006",
    "雷丘": "026",
}


def test_fetch_official_ma1_pokemon_list_parses_unique_codes_and_internal_mapping_fields():
    from scripts.champions.sources.official import fetch_official_ma1_pokemon_list

    result = fetch_official_ma1_pokemon_list(
        html_fetcher=lambda url: OFFICIAL_MA1_HTML,
        pokemon_index=POKEMON_ZH_INDEX,
        aliases_zh=ALIASES_ZH,
    )

    assert result["meta"]["source"] == "pokemonchampions-official"
    assert result["meta"]["season"] == "MA1"
    assert result["meta"]["event_id"] == "rs177501629259kmzbny"
    assert result["meta"]["pokemon_count"] == 3
    assert result["files"]["pokemon.json"] == [
        {
            "code": "0003-000",
            "dex_no": "0003",
            "form_no": "000",
            "slug": "0003-000",
            "name_ja": "フシギバナ",
            "base_name_ja": "フシギバナ",
            "form_name_ja": None,
            "is_form": False,
            "pokemon_id": "003",
            "name_zh": "妙蛙花",
            "name_en": "Venusaur",
            "match_key": "妙蛙花",
            "alias_keys": ["妙蛙花"],
        },
        {
            "code": "0006-000",
            "dex_no": "0006",
            "form_no": "000",
            "slug": "0006-000",
            "name_ja": "リザードン",
            "base_name_ja": "リザードン",
            "form_name_ja": None,
            "is_form": False,
            "pokemon_id": "006",
            "name_zh": "喷火龙",
            "name_en": "Charizard",
            "match_key": "喷火龙",
            "alias_keys": ["喷火龙"],
        },
        {
            "code": "0026-001",
            "dex_no": "0026",
            "form_no": "001",
            "slug": "0026-001",
            "name_ja": "ライチュウ (アローラのすがた)",
            "base_name_ja": "ライチュウ",
            "form_name_ja": "アローラのすがた",
            "is_form": True,
            "pokemon_id": "026",
            "name_zh": "雷丘",
            "name_en": "Raichu",
            "match_key": "雷丘",
            "alias_keys": ["雷丘"],
        },
    ]


def test_build_default_fetchers_uses_official_ma1_source():
    from scripts.champions.update_database import build_default_fetchers

    fetchers = build_default_fetchers()

    assert "official" in fetchers
    assert callable(fetchers["official"])


def test_run_update_writes_official_ma1_pokemon_json_and_manifest(tmp_path: Path):
    from scripts.champions.update_database import run_update

    summary = run_update(
        data_root=tmp_path / "data" / "champions",
        official_html_fetcher=lambda url: OFFICIAL_MA1_HTML,
        version_provider=lambda: "2026-04-19_103500",
        pokemon_index=POKEMON_ZH_INDEX,
        aliases_zh=ALIASES_ZH,
    )

    current_dir = tmp_path / "data" / "champions" / "current"
    pokemon_path = current_dir / "pokemon.json"
    manifest_path = current_dir / "source-manifest.json"

    assert summary["version"] == "2026-04-19_103500"
    assert pokemon_path.exists()
    assert manifest_path.exists()
    pokemon = json.loads(pokemon_path.read_text(encoding="utf-8"))
    assert pokemon[0]["name_zh"] == "妙蛙花"
    assert pokemon[1]["name_en"] == "Charizard"
    assert pokemon[-1]["match_key"] == "雷丘"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["sources"]["official"]["source"] == "pokemonchampions-official"
    assert manifest["sources"]["official"]["event_id"] == "rs177501629259kmzbny"
