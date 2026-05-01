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
        "player_status_panel": {"x": 0.015625, "y": 0.802083, "w": 0.328125, "h": 0.1875, "confidence": "fixed"},
        "opponent_status_panel": {"x": 0.710938, "y": 0.03125, "w": 0.28125, "h": 0.1875, "confidence": "fixed"},
        "move_list": {"x": 0.695312, "y": 0.416667, "w": 0.296875, "h": 0.552083, "confidence": "fixed"},
        # 全流程追踪 v2：HP 区域
        "player_hp_text": {"x": 0.02, "y": 0.80, "w": 0.33, "h": 0.19, "confidence": "calibrated"},
        "opponent_hp_bar": {"x": 0.65, "y": 0.02, "w": 0.33, "h": 0.20, "confidence": "calibrated"},
        # 全流程追踪 v2：技能 4 分格
        "move_slot_1": {"x": 0.738, "y": 0.498, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
        "move_slot_2": {"x": 0.738, "y": 0.618, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
        "move_slot_3": {"x": 0.738, "y": 0.738, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
        "move_slot_4": {"x": 0.738, "y": 0.858, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
    },
    "battle_move_menu_open": {
        "player_status_panel": {"x": 0.015625, "y": 0.802083, "w": 0.328125, "h": 0.1875, "confidence": "fixed"},
        "opponent_status_panel": {"x": 0.710938, "y": 0.03125, "w": 0.28125, "h": 0.1875, "confidence": "fixed"},
        "move_list": {"x": 0.695312, "y": 0.416667, "w": 0.296875, "h": 0.552083, "confidence": "fixed"},
        "player_hp_text": {"x": 0.02, "y": 0.80, "w": 0.33, "h": 0.19, "confidence": "calibrated"},
        "opponent_hp_bar": {"x": 0.65, "y": 0.02, "w": 0.33, "h": 0.20, "confidence": "calibrated"},
        "move_slot_1": {"x": 0.738, "y": 0.498, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
        "move_slot_2": {"x": 0.738, "y": 0.618, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
        "move_slot_3": {"x": 0.738, "y": 0.738, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
        "move_slot_4": {"x": 0.738, "y": 0.858, "w": 0.242, "h": 0.112, "confidence": "calibrated"},
    },
    "team_select_default": {
        "instruction_banner": {"x": 0.31, "y": 0.10, "w": 0.38, "h": 0.08, "confidence": "approx"},
        # 全流程追踪 v2：我方 6 只独立锚点
        "player_mon_1": {"x": 0.02, "y": 0.12, "w": 0.33, "h": 0.117, "confidence": "calibrated"},
        "player_mon_2": {"x": 0.02, "y": 0.237, "w": 0.33, "h": 0.117, "confidence": "calibrated"},
        "player_mon_3": {"x": 0.02, "y": 0.353, "w": 0.33, "h": 0.117, "confidence": "calibrated"},
        "player_mon_4": {"x": 0.02, "y": 0.47, "w": 0.33, "h": 0.117, "confidence": "calibrated"},
        "player_mon_5": {"x": 0.02, "y": 0.587, "w": 0.33, "h": 0.117, "confidence": "calibrated"},
        "player_mon_6": {"x": 0.02, "y": 0.703, "w": 0.33, "h": 0.117, "confidence": "calibrated"},
        # 全流程追踪 v2：对方 6 只独立锚点（右侧50%区域）
        "opponent_mon_1": {"x": 0.82, "y": 0.12, "w": 0.16, "h": 0.117, "confidence": "calibrated"},
        "opponent_mon_2": {"x": 0.82, "y": 0.237, "w": 0.16, "h": 0.117, "confidence": "calibrated"},
        "opponent_mon_3": {"x": 0.82, "y": 0.353, "w": 0.16, "h": 0.117, "confidence": "calibrated"},
        "opponent_mon_4": {"x": 0.82, "y": 0.47, "w": 0.16, "h": 0.117, "confidence": "calibrated"},
        "opponent_mon_5": {"x": 0.82, "y": 0.587, "w": 0.16, "h": 0.117, "confidence": "calibrated"},
        "opponent_mon_6": {"x": 0.82, "y": 0.703, "w": 0.16, "h": 0.117, "confidence": "calibrated"},
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
