from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_allows_frontend_origin_for_browser_requests():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
