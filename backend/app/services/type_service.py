from __future__ import annotations

from app.schemas.types import (
    CombinedTypeMatchupsResponse,
    TypeAttackMatchups,
    TypeDefenseMatchups,
    TypeMatchupsResponse,
)
from app.services.data_loader import EXPECTED_TYPES, load_type_chart

EN_TO_ZH_TYPE = {
    "normal": "一般",
    "fire": "火",
    "water": "水",
    "electric": "电",
    "grass": "草",
    "ice": "冰",
    "fighting": "格斗",
    "poison": "毒",
    "ground": "地面",
    "flying": "飞行",
    "psychic": "超能力",
    "bug": "虫",
    "rock": "岩石",
    "ghost": "幽灵",
    "dragon": "龙",
    "dark": "恶",
    "steel": "钢",
    "fairy": "妖精",
}


class TypeService:
    def __init__(self) -> None:
        self._chart = load_type_chart()

    def get_matchups(self, raw_type_name: str) -> TypeMatchupsResponse:
        type_name = self._normalize_type(raw_type_name)
        attack_map = self._chart[type_name]

        attack = TypeAttackMatchups(
            strong_against=sorted([name for name, value in attack_map.items() if value > 1.0]),
            weak_against=sorted([name for name, value in attack_map.items() if 0.0 < value < 1.0]),
            no_effect_against=sorted([name for name, value in attack_map.items() if value == 0.0]),
        )

        defense_values = {
            attack_type: self._chart[attack_type][type_name]
            for attack_type in self._chart
        }
        defense = TypeDefenseMatchups(
            weak_to=sorted([name for name, value in defense_values.items() if value > 1.0]),
            resists=sorted([name for name, value in defense_values.items() if 0.0 < value < 1.0]),
            immune_to=sorted([name for name, value in defense_values.items() if value == 0.0]),
        )

        return TypeMatchupsResponse(type_name=type_name, attack=attack, defense=defense)

    def get_combined_matchups(self, raw_types: list[str]) -> CombinedTypeMatchupsResponse:
        if not 1 <= len(raw_types) <= 2:
            raise ValueError("types 必须包含 1 到 2 个属性")

        normalized_types = [self._normalize_type(type_name) for type_name in raw_types]
        defense_multipliers: dict[str, float] = {}
        for attack_type in EXPECTED_TYPES:
            multiplier = 1.0
            for defense_type in normalized_types:
                multiplier *= self._chart[attack_type][defense_type]
            defense_multipliers[attack_type] = multiplier

        return CombinedTypeMatchupsResponse(
            types=normalized_types,
            defense_multipliers=dict(sorted(defense_multipliers.items())),
        )

    def _normalize_type(self, raw_type_name: str) -> str:
        candidate = raw_type_name.strip()
        if not candidate:
            raise ValueError("属性不能为空")
        if candidate in EXPECTED_TYPES:
            return candidate

        mapped = EN_TO_ZH_TYPE.get(candidate.lower())
        if mapped is not None:
            return mapped

        raise ValueError(f"未知属性: {raw_type_name}")
