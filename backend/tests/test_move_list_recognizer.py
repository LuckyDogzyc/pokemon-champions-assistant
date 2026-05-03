from app.services.recognizers.move_list_recognizer import MoveListRecognizer


class StubOcrAdapter:
    def __init__(self, texts):
        self._texts = texts

    def read_text(self, frame, roi):
        return [{"text": text, "score": 0.9} for text in self._texts]


def test_move_list_recognizer_matches_known_move_names_not_pokemon_names() -> None:
    recognizer = MoveListRecognizer(ocr_adapter=StubOcrAdapter(["Flamethrowr", "PP 7/15"]))

    result = recognizer.recognize_slot({"width": 200, "height": 80})

    assert result["name"] == "Flamethrower"
    assert result["pp_current"] == 7
    assert result["pp_max"] == 15
    assert result["confidence"] >= 0.8
