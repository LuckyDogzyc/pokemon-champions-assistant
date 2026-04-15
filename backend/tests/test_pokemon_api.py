from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_endpoint_returns_matching_pokemon():
    response = client.get("/api/pokemon/search", params={"q": "喷火龙"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "喷火龙"
    assert len(payload["results"]) >= 1
    first = payload["results"][0]
    assert first["canonical_name"] == "喷火龙"
    assert first["match_type"] == "exact"
    assert first["pokemon"]["id"] == "006"


def test_search_endpoint_supports_alias_queries():
    response = client.get("/api/pokemon/search", params={"q": "老喷"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["canonical_name"] == "喷火龙"
    assert payload["results"][0]["match_type"] == "alias"


def test_detail_endpoint_returns_exact_pokemon_profile():
    response = client.get("/api/pokemon/喷火龙")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_name"] == "喷火龙"
    assert payload["match_type"] == "exact"
    assert payload["pokemon"]["id"] == "006"
    assert payload["pokemon"]["types"] == ["火", "飞行"]


def test_detail_endpoint_uses_fuzzy_match_for_minor_ocr_error():
    response = client.get("/api/pokemon/喷火龟")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_name"] == "喷火龙"
    assert payload["match_type"] == "fuzzy"
    assert payload["pokemon"]["id"] == "006"


def test_detail_endpoint_returns_404_for_unknown_pokemon():
    response = client.get("/api/pokemon/完全不相关")

    assert response.status_code == 404
    assert response.json()["detail"] == "未找到匹配的宝可梦"
