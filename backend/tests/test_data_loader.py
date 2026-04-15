from app.services.data_loader import (
    load_aliases,
    load_pokemon_index,
    load_type_chart,
)


EXPECTED_TYPES = {
    "一般",
    "火",
    "水",
    "电",
    "草",
    "冰",
    "格斗",
    "毒",
    "地面",
    "飞行",
    "超能力",
    "虫",
    "岩石",
    "幽灵",
    "龙",
    "恶",
    "钢",
    "妖精",
}


def test_load_pokemon_index_returns_minimum_seed_data():
    pokemon_index = load_pokemon_index()

    assert isinstance(pokemon_index, list)
    assert len(pokemon_index) >= 6

    sample = next(p for p in pokemon_index if p["id"] == "001")
    assert sample["name_zh"] == "妙蛙种子"
    assert sample["types"] == ["草", "毒"]


def test_pokemon_entries_and_aliases_follow_expected_schema():
    pokemon_index = load_pokemon_index()
    aliases = load_aliases()
    known_ids = {entry["id"] for entry in pokemon_index}

    for entry in pokemon_index:
        assert set(entry.keys()) >= {"id", "name_zh", "types"}
        assert isinstance(entry["id"], str)
        assert entry["id"].isdigit()
        assert 3 <= len(entry["id"]) <= 4
        assert isinstance(entry["name_zh"], str)
        assert entry["name_zh"]
        assert isinstance(entry["types"], list)
        assert 1 <= len(entry["types"]) <= 2
        assert set(entry["types"]).issubset(EXPECTED_TYPES)

    for alias_target in aliases.values():
        assert alias_target in known_ids


def test_load_aliases_supports_common_zh_names():
    aliases = load_aliases()

    assert isinstance(aliases, dict)
    assert aliases["皮神"] == "025"
    assert aliases["喷火龙"] == "006"


def test_load_type_chart_contains_complete_18_type_matrix():
    type_chart = load_type_chart()

    assert set(type_chart.keys()) == EXPECTED_TYPES
    for attack_type in EXPECTED_TYPES:
        defense_map = type_chart[attack_type]
        assert set(defense_map.keys()) == EXPECTED_TYPES
        assert set(defense_map.values()).issubset({0.0, 0.5, 1.0, 2.0})

    assert type_chart["火"]["草"] == 2.0
    assert type_chart["电"]["地面"] == 0.0
    assert type_chart["妖精"]["龙"] == 2.0
    assert type_chart["一般"]["幽灵"] == 0.0


def test_data_loader_returns_defensive_copies():
    aliases = load_aliases()
    aliases["临时别名"] = "001"

    pokemon_index = load_pokemon_index()
    pokemon_index[0]["name_zh"] = "被污染的数据"

    type_chart = load_type_chart()
    type_chart["火"]["草"] = 1.0

    fresh_aliases = load_aliases()
    fresh_pokemon_index = load_pokemon_index()
    fresh_type_chart = load_type_chart()

    assert "临时别名" not in fresh_aliases
    assert fresh_pokemon_index[0]["name_zh"] != "被污染的数据"
    assert fresh_type_chart["火"]["草"] == 2.0
