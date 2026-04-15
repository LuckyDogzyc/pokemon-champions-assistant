from __future__ import annotations

from pydantic import BaseModel, Field


class TypeAttackMatchups(BaseModel):
    strong_against: list[str] = Field(default_factory=list)
    weak_against: list[str] = Field(default_factory=list)
    no_effect_against: list[str] = Field(default_factory=list)


class TypeDefenseMatchups(BaseModel):
    weak_to: list[str] = Field(default_factory=list)
    resists: list[str] = Field(default_factory=list)
    immune_to: list[str] = Field(default_factory=list)


class TypeMatchupsResponse(BaseModel):
    type_name: str
    attack: TypeAttackMatchups
    defense: TypeDefenseMatchups


class CombinedTypesRequest(BaseModel):
    types: list[str]


class CombinedTypeMatchupsResponse(BaseModel):
    types: list[str]
    defense_multipliers: dict[str, float]
