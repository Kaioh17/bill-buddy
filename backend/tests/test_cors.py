def test_preflight_allowed_origin(client):
    r = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-credentials"] == "true"


def test_preflight_unknown_origin_gets_no_allow_header(client):
    r = client.options(
        "/auth/login",
        headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in r.headers


def test_renewed_token_header_is_exposed(client):
    r = client.get("/health/", headers={"Origin": "http://localhost:5173"})
    assert "x-access-token" in r.headers["access-control-expose-headers"].lower()
