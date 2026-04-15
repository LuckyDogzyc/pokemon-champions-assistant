from app.services.name_matcher import NameMatcher


def test_name_matcher_returns_exact_match_for_canonical_name():
    matcher = NameMatcher()

    result = matcher.match("喷火龙")

    assert result.found is True
    assert result.match_type == "exact"
    assert result.canonical_name == "喷火龙"
    assert result.pokemon_id == "006"
    assert result.score == 100.0


def test_name_matcher_resolves_alias_to_canonical_name():
    matcher = NameMatcher()

    result = matcher.match("老喷")

    assert result.found is True
    assert result.match_type == "alias"
    assert result.canonical_name == "喷火龙"
    assert result.pokemon_id == "006"


def test_name_matcher_supports_fuzzy_match_for_minor_ocr_error():
    matcher = NameMatcher()

    result = matcher.match("喷火龟")

    assert result.found is True
    assert result.match_type == "fuzzy"
    assert result.canonical_name == "喷火龙"
    assert result.pokemon_id == "006"
    assert result.score >= 60.0


def test_name_matcher_returns_not_found_when_query_is_too_far_off():
    matcher = NameMatcher()

    result = matcher.match("完全不相关")

    assert result.found is False
    assert result.match_type == "none"
    assert result.canonical_name is None
    assert result.pokemon_id is None
