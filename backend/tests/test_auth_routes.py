from datetime import timedelta

from fastapi.testclient import TestClient

from app.auth.oauth2 import CurrentUser
from app.auth.session import SESSION_HEADER
from app.auth.tokens import create_access_token
from tests.conftest import GOOD_SIGNUP


def login(client, email="ada@example.com", password=GOOD_SIGNUP["password"]):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_signup_created(client):
    r = client.post("/auth/signup", json=GOOD_SIGNUP)
    assert r.status_code == 201
    body = r.json()
    assert body["data"]["email"] == "ada@example.com"
    assert body["data"]["first_name"] == "Ada"
    assert "password" not in r.text and "hash" not in r.text
    assert body["meta"] == {"count": None}


def test_signup_duplicate_is_409_with_error_shape(client):
    client.post("/auth/signup", json=GOOD_SIGNUP)
    r = client.post("/auth/signup", json=GOOD_SIGNUP)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_already_registered"


def test_signup_mismatch_is_422_and_never_echoes_password(client):
    r = client.post(
        "/auth/signup", json={**GOOD_SIGNUP, "confirm_password": "different one here"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert GOOD_SIGNUP["password"] not in r.text
    assert "different one here" not in r.text


def test_signup_short_password_422(client):
    r = client.post(
        "/auth/signup",
        json={**GOOD_SIGNUP, "password": "short", "confirm_password": "short"},
    )
    assert r.status_code == 422


def test_login_ok(client):
    client.post("/auth/signup", json=GOOD_SIGNUP)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    assert body["access_token"]


def test_login_failures_are_401_and_generic(client):
    client.post("/auth/signup", json=GOOD_SIGNUP)
    a = login(client, password="wrong password here")
    b = login(client, email="nobody@example.com")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()
    assert a.headers["www-authenticate"] == "Bearer"


def test_login_is_case_insensitive_on_email(client):
    client.post("/auth/signup", json=GOOD_SIGNUP)
    assert login(client, email="ADA@Example.com").status_code == 200


def test_login_form_endpoint(client):
    client.post("/auth/signup", json=GOOD_SIGNUP)
    r = client.post(
        "/auth/login",
        data={"username": "ada@example.com", "password": GOOD_SIGNUP["password"]},
    )
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    r = client.post(
        "/auth/login",
        data={"username": "ada@example.com", "password": "wrong password here"},
    )
    assert r.status_code == 401
    r = client.post(
        "/auth/login", data={"username": "ada@example.com", "password": "x" * 500}
    )
    assert r.status_code == 401  # over the length cap: same answer as a wrong password


def protected(app):
    @app.get("/_whoami")
    def whoami(user: CurrentUser):
        return {"sub": user.sub}

    return TestClient(app)


def test_protected_route_requires_token(app):
    c = protected(app)
    r = c.get("/_whoami")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"
    assert r.headers["www-authenticate"] == "Bearer"


def test_protected_route_accepts_token_and_renews_it(app):
    c = protected(app)
    r = c.get(
        "/_whoami", headers={"Authorization": f"Bearer {create_access_token('u1')}"}
    )
    assert r.status_code == 200 and r.json() == {"sub": "u1"}
    assert SESSION_HEADER in r.headers


def test_protected_route_rejects_bad_and_expired(app):
    c = protected(app)
    r = c.get("/_whoami", headers={"Authorization": "Bearer nope"})
    assert (r.status_code, r.json()["error"]["code"]) == (401, "invalid_token")
    expired = create_access_token("u1", expires_delta=timedelta(seconds=-5))
    r = c.get("/_whoami", headers={"Authorization": f"Bearer {expired}"})
    assert (r.status_code, r.json()["error"]["code"]) == (401, "token_expired")


def test_login_is_form_only(client):
    r = client.post("/auth/login", json={"email": "a@b.co", "password": "x"})
    assert r.status_code == 422  # JSON body is not accepted
    assert client.post("/auth/token", data={}).status_code == 404


def test_swagger_authorize_points_at_login(app):
    # The scheme only shows in the docs once a route depends on CurrentUser.
    spec = protected(app).get("/openapi.json").json()
    schemes = spec["components"]["securitySchemes"]
    assert next(iter(schemes.values()))["flows"]["password"]["tokenUrl"] == "auth/login"
