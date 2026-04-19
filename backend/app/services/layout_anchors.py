from __future__ import annotations

from copy import deepcopy


DEFAULT_LAYOUTS = {
    "battle_default": {
        "player_name": {"x": 0.08, "y": 0.80, "w": 0.22, "h": 0.07, "confidence": "approx"},
        "player_status_panel": {"x": 0.02, "y": 0.78, "w": 0.25, "h": 0.14, "confidence": "approx"},
        "opponent_name": {"x": 0.70, "y": 0.10, "w": 0.22, "h": 0.07, "confidence": "approx"},
        "opponent_status_panel": {"x": 0.69, "y": 0.03, "w": 0.28, "h": 0.13, "confidence": "approx"},
        "command_panel": {"x": 0.77, "y": 0.40, "w": 0.18, "h": 0.16, "confidence": "approx"},
    },
    "battle_move_menu_open": {
        "player_name": {"x": 0.08, "y": 0.80, "w": 0.22, "h": 0.07, "confidence": "approx"},
        "player_status_panel": {"x": 0.02, "y": 0.78, "w": 0.25, "h": 0.14, "confidence": "approx"},
        "opponent_name": {"x": 0.70, "y": 0.10, "w": 0.20, "h": 0.07, "confidence": "approx"},
        "opponent_status_panel": {"x": 0.69, "y": 0.03, "w": 0.28, "h": 0.13, "confidence": "approx"},
        "command_panel": {"x": 0.77, "y": 0.40, "w": 0.18, "h": 0.16, "confidence": "approx"},
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

    width = int(frame_or_annotation.get("width", 1920))
    height = int(frame_or_annotation.get("height", 1080))
    return {
        "player_name": {
            "x": round(0.08, 4),
            "y": round(0.80, 4),
            "w": round(0.22, 4),
            "h": round(0.07, 4),
            "confidence": "approx",
        },
        "opponent_name": {
            "x": round(0.70, 4),
            "y": round(0.10, 4),
            "w": round(0.22, 4),
            "h": round(0.07, 4),
            "confidence": "approx",
        },
        "frame_size_hint": {
            "x": float(width),
            "y": float(height),
            "w": 0.0,
            "h": 0.0,
            "confidence": "approx",
        },
    }


def get_battle_name_anchors(frame: dict) -> dict[str, dict[str, float | str]]:
    anchors = get_layout_anchors(frame)
    return {
        "player": deepcopy(anchors["player_name"]),
        "opponent": deepcopy(anchors["opponent_name"]),
    }
