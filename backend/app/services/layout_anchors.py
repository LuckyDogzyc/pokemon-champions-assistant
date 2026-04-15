from __future__ import annotations


def get_battle_name_anchors(frame: dict) -> dict[str, dict[str, int]]:
    width = int(frame.get("width", 1920))
    height = int(frame.get("height", 1080))
    return {
        "player": {
            "x": int(width * 0.08),
            "y": int(height * 0.80),
            "width": int(width * 0.22),
            "height": int(height * 0.07),
        },
        "opponent": {
            "x": int(width * 0.70),
            "y": int(height * 0.10),
            "width": int(width * 0.22),
            "height": int(height * 0.07),
        },
    }
