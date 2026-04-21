def test_health_check(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_homepage_head_request_returns_ok(client) -> None:
    response = client.head("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
