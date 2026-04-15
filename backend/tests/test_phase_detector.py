from app.services.phase_detector import PhaseDetector


def test_phase_detector_returns_supported_phase_values():
    detector = PhaseDetector()

    assert detector.detect({"ui": {"team_select_banner": True}}).phase == "team_select"
    assert detector.detect({"ui": {"switch_prompt": True}}).phase == "switching"
    assert detector.detect({"ui": {"battle_hud": True}}).phase == "battle"
    assert detector.detect({"ui": {"move_resolution_text": True}}).phase == "move_resolution"
    assert detector.detect({"ui": {}}).phase == "unknown"


def test_phase_detector_returns_confidence_and_anchor_evidence():
    detector = PhaseDetector()

    result = detector.detect({"ui": {"battle_hud": True}})

    assert result.phase == "battle"
    assert result.confidence > 0
    assert "battle_hud" in result.evidence
