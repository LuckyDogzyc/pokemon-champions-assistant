from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "pokemon"
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
VALID_MULTIPLIERS = {0.0, 0.5, 1.0, 2.0}


def _load_json(filename: str) -> Any:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as file:
        return json.load(file)


def _validate_pokemon_index(pokemon_index: Any) -> list[dict[str, Any]]:
    if not isinstance(pokemon_index, list):
        raise ValueError("pokemon_zh_index.json 必须是列表")

    for entry in pokemon_index:
        if not isinstance(entry, dict):
            raise ValueError("pokemon_zh_index.json 中的每一项必须是对象")
        if not {"id", "name_zh", "types"}.issubset(entry):
            raise ValueError("宝可梦条目缺少必填字段")
        if not isinstance(entry["id"], str) or len(entry["id"]) != 3:
            raise ValueError("宝可梦 id 必须是 3 位字符串")
        if not isinstance(entry["name_zh"], str) or not entry["name_zh"]:
            raise ValueError("宝可梦中文名必须是非空字符串")
        if not isinstance(entry["types"], list) or not 1 <= len(entry["types"]) <= 2:
            raise ValueError("宝可梦属性必须是长度 1 到 2 的列表")
        if not set(entry["types"]).issubset(EXPECTED_TYPES):
            raise ValueError("宝可梦属性包含非法类型")

    return pokemon_index


def _validate_aliases(aliases: Any, pokemon_index: list[dict[str, Any]]) -> dict[str, str]:
    if not isinstance(aliases, dict):
        raise ValueError("aliases_zh.json 必须是对象")

    known_ids = {entry["id"] for entry in pokemon_index}
    for alias, target_id in aliases.items():
        if not isinstance(alias, str) or not alias:
            raise ValueError("alias key 必须是非空字符串")
        if target_id not in known_ids:
            raise ValueError("alias target 必须指向已存在的宝可梦 id")

    return aliases


def _validate_type_chart(type_chart: Any) -> dict[str, dict[str, float]]:
    if not isinstance(type_chart, dict) or set(type_chart.keys()) != EXPECTED_TYPES:
        raise ValueError("type_chart.json 必须包含完整 18 属性键")

    for attack_type, defense_map in type_chart.items():
        if not isinstance(defense_map, dict) or set(defense_map.keys()) != EXPECTED_TYPES:
            raise ValueError(f"{attack_type} 的防守映射不完整")
        if not set(defense_map.values()).issubset(VALID_MULTIPLIERS):
            raise ValueError(f"{attack_type} 的倍率包含非法值")

    return type_chart


@lru_cache
def _load_pokemon_index_cached() -> list[dict[str, Any]]:
    return _validate_pokemon_index(_load_json("pokemon_zh_index.json"))


@lru_cache
def _load_aliases_cached() -> dict[str, str]:
    return _validate_aliases(_load_json("aliases_zh.json"), _load_pokemon_index_cached())


@lru_cache
def _load_type_chart_cached() -> dict[str, dict[str, float]]:
    return _validate_type_chart(_load_json("type_chart.json"))


def load_pokemon_index() -> list[dict[str, Any]]:
    return copy.deepcopy(_load_pokemon_index_cached())



def load_aliases() -> dict[str, str]:
    return copy.deepcopy(_load_aliases_cached())



def load_type_chart() -> dict[str, dict[str, float]]:
    return copy.deepcopy(_load_type_chart_cached())
