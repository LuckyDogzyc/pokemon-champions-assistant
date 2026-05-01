from __future__ import annotations

from app.models.phase_state import PhaseState
from app.schemas.phase import BattlePhase, PhaseDetectionResult


class PhaseDetector:
    def detect(self, frame: dict) -> PhaseDetectionResult:
        if isinstance(frame, dict) and frame.get("ocr_texts"):
            state = self._detect_from_texts(frame.get("ocr_texts", []), frame.get("layout_variant_hint"))
        else:
            ui = frame.get("ui", {}) if isinstance(frame, dict) else {}
            state = self._detect_state(ui)
        return PhaseDetectionResult(
            phase=state.phase,
            confidence=state.confidence,
            evidence=state.evidence,
        )

    def _detect_state(self, ui: dict) -> PhaseState:
        if ui.get("team_select_banner"):
            return PhaseState(
                phase=BattlePhase.TEAM_SELECT,
                confidence=0.95,
                evidence=["team_select_banner"],
            )
        if ui.get("switch_prompt"):
            return PhaseState(
                phase=BattlePhase.SWITCHING,
                confidence=0.9,
                evidence=["switch_prompt"],
            )
        if ui.get("move_resolution_text"):
            return PhaseState(
                phase=BattlePhase.MOVE_RESOLUTION,
                confidence=0.85,
                evidence=["move_resolution_text"],
            )
        if ui.get("battle_hud"):
            return PhaseState(
                phase=BattlePhase.BATTLE,
                confidence=0.9,
                evidence=["battle_hud"],
            )
        return PhaseState()

    def _detect_from_texts(self, ocr_texts: list[str], layout_variant_hint: str | None) -> PhaseState:
        texts = [str(item).strip() for item in ocr_texts if str(item).strip()]
        joined = " ".join(texts)

        team_select_hits = [
            text for text in texts
            if "请选择出3只要上场战斗的宝可梦" in text or text == "选择完毕" or text == "0/3"
        ]
        if layout_variant_hint == "team_select_default" or len(team_select_hits) >= 2:
            return PhaseState(
                phase=BattlePhase.TEAM_SELECT,
                confidence=0.95 if layout_variant_hint == "team_select_default" else 0.85,
                evidence=team_select_hits or [joined],
            )

        battle_hits = [
            text for text in texts
            if text.upper().startswith("COMMAND") or "查看状态" in text or "招式说明" in text
        ]
        named_pokemon_hits = [
            text for text in texts if any(name in text for name in ["烈咬陆鲨", "雪妖女", "大竺葵"])
        ]
        if layout_variant_hint in {"battle_default", "battle_move_menu_open"} or battle_hits:
            evidence = battle_hits + named_pokemon_hits
            return PhaseState(
                phase=BattlePhase.BATTLE,
                confidence=0.95 if layout_variant_hint in {"battle_default", "battle_move_menu_open"} else 0.85,
                evidence=evidence or [joined],
            )

        # 结算检测：胜利/失败/战斗结束等关键词
        final_result_hits = [
            text for text in texts
            if any(kw in text for kw in ["胜利", "获胜", "你赢了", "失败", "你输了", "战斗结束", "WINNER"])
        ]
        if final_result_hits:
            return PhaseState(
                phase=BattlePhase.FINAL_RESULT,
                confidence=0.9,
                evidence=final_result_hits,
            )

        return PhaseState()
