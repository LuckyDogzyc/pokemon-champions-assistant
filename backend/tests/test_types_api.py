from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_single_type_matchups_returns_attack_and_defense_views():
    response = client.get("/api/type/Fire/matchups")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type_name"] == "火"
    assert "草" in payload["attack"]["strong_against"]
    assert "龙" in payload["attack"]["weak_against"]
    assert "地面" in payload["defense"]["weak_to"]
    assert "妖精" in payload["defense"]["resists"]


def test_get_combined_type_matchups_returns_dual_type_defense_chart():
    response = client.post(
        "/api/type/combined-matchups",
        json={"types": ["Fire", "Flying"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["types"] == ["火", "飞行"]
    assert payload["defense_multipliers"]["地面"] == 0.0
    assert payload["defense_multipliers"]["岩石"] == 4.0
    assert payload["defense_multipliers"]["草"] == 0.25
