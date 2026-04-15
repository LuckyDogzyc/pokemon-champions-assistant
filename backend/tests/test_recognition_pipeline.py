from app.services.recognition_pipeline import RecognitionPipeline


class StubPhaseDetector:
    def detect(self, frame):
        from app.schemas.phase import PhaseDetectionResult

        return PhaseDetectionResult(
            phase="battle",
            confidence=0.95,
            evidence=["battle_hud"],
        )


class StubRecognizer:
    def recognize_side(self, frame, roi, side):
        if side == "player":
            return {"name": "喷火龙", "confidence": 0.99, "source": "mock", "roi": roi}
        return {"name": "皮卡丘", "confidence": 0.88, "source": "mock", "roi": roi}


def test_recognition_pipeline_uses_phase_and_anchors_for_battle_phase():
    pipeline = RecognitionPipeline(
        phase_detector=StubPhaseDetector(),
        recognizer=StubRecognizer(),
    )

    result = pipeline.recognize({"width": 1920, "height": 1080, "timestamp": "2026-04-15T15:00:00Z"})

    assert result.current_phase == "battle"
    assert result.player_active_name == "喷火龙"
    assert result.opponent_active_name == "皮卡丘"
    assert result.player.source == "mock"
    assert result.opponent.source == "mock"


def test_recognition_pipeline_skips_name_recognition_when_not_in_battle():
    class NonBattleDetector:
        def detect(self, frame):
            from app.schemas.phase import PhaseDetectionResult

            return PhaseDetectionResult(
                phase="team_select",
                confidence=0.9,
                evidence=["team_select_banner"],
            )

    pipeline = RecognitionPipeline(
        phase_detector=NonBattleDetector(),
        recognizer=StubRecognizer(),
    )

    result = pipeline.recognize({"width": 1280, "height": 720, "timestamp": "2026-04-15T15:01:00Z"})

    assert result.current_phase == "team_select"
    assert result.player_active_name is None
    assert result.opponent_active_name is None
