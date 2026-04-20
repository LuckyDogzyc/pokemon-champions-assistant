from __future__ import annotations

from copy import deepcopy


BATTLE_NAME_ANCHORS = {
    "battle_default": {
        "player": {"x": 0.08, "y": 0.80, "w": 0.22, "h": 0.07, "confidence": "approx"},
        "opponent": {"x": 0.70, "y": 0.10, "w": 0.22, "h": 0.07, "confidence": "approx"},
    },
    "battle_move_menu_open": {
        "player": {"x": 0.08, "y": 0.80, "w": 0.22, "h": 0.07, "confidence": "approx"},
        "opponent": {"x": 0.70, "y": 0.10, "w": 0.20, "h": 0.07, "confidence": "approx"},
    },
}


DEFAULT_LAYOUTS = {
    "battle_default": {
        "player_status_panel": {"x": 0.0469, "y": 0.8167, "w": 0.3203, "h": 0.1708, "confidence": "approx"},
        "opponent_status_panel": {"x": 0.7109, "y": 0.0375, "w": 0.2578, "h": 0.15, "confidence": "approx"},
    },
    "battle_move_menu_open": {
        "player_status_panel": {"x": 0.0469, "y": 0.8167, "w": 0.3203, "h": 0.1708, "confidence": "approx"},
        "opponent_status_panel": {"x": 0.7109, "y": 0.0375, "w": 0.2578, "h": 0.15, "confidence": "approx"},
        "move_list": {"x": 0.73, "y": 0.43, "w": 0.23, "h": 0.36, "confidence": "approx"},
    },
    "team_select_default": {
        "instruction_banner": {"x": 0.31, "y": 0.10, "w": 0.38, "h": 0.08, "confidence": "approx"},
        "player_team_list": {"x": 0.03, "y": 0.15, "w": 0.32, "h": 0.62, "confidence": "approx"},
        "opponent_team_list": {"x": 0.69, "y": 0.15, "w": 0.27, "h": 0.62, "confidence": "approx"},
    },
}


def get_layout_anchors(frame_or_annotation: dict) -> dict[str, dict[str, float | str]]:
    roi_candidates = frame_or_annotation.get("roi_candidates")
    if isinstance(roi_candidates, dict) and roi_candidates:
        return deepcopy(roi_candidates)

    layout_variant = frame_or_annotation.get("layout_variant") or frame_or_annotation.get("layout_variant_hint")
    if layout_variant in DEFAULT_LAYOUTS:
        return deepcopy(DEFAULT_LAYOUTS[layout_variant])

    phase = frame_or_annotation.get("phase")
    if isinstance(phase, dict):
        expected_phase = phase.get("expected_phase")
        if expected_phase == "team_select":
            return deepcopy(DEFAULT_LAYOUTS["team_select_default"])
        if expected_phase == "battle":
            return deepcopy(DEFAULT_LAYOUTS["battle_default"])

    return {}


def get_battle_name_anchors(frame: dict) -> dict[str, dict[str, float | str]]:
    layout_variant = frame.get("layout_variant") or frame.get("layout_variant_hint")
    battle_anchors = BATTLE_NAME_ANCHORS.get(layout_variant or "", BATTLE_NAME_ANCHORS["battle_default"])
    return {
        "player": deepcopy(battle_anchors["player"]),
        "opponent": deepcopy(battle_anchors["opponent"]),
    }
