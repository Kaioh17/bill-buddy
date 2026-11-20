import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exception import (
    AppException,
    ConflictError,
    EmailAlreadyRegisteredError,
    ForbiddenError,
    InvalidCredentialsError,
    NotFoundError,
    UnauthorizedError,
    register_exception_handlers,
)


class Body(BaseModel):
    password: str
    n: int


def build():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-exc")
    def a():
        raise EmailAlreadyRegisteredError()

    @app.get("/boom")
    def b():
        raise RuntimeError("db password is hunter2")

    @app.post("/body")
    def c(body: Body):
        return {}

    return app


@pytest.mark.parametrize(
    "cls,status",
    [
        (NotFoundError, 404),
        (ForbiddenError, 403),
        (ConflictError, 409),
        (UnauthorizedError, 401),
    ],
)
def test_http_exceptions_have_status(cls, status):
    assert issubclass(cls, AppException)
    assert cls().status_code == status


def test_logic_exceptions_have_codes():
    assert EmailAlreadyRegisteredError().code == "email_already_registered"
    assert EmailAlreadyRegisteredError().status_code == 409
    assert InvalidCredentialsError().status_code == 401
    assert "WWW-Authenticate" in InvalidCredentialsError().headers


def test_app_exception_response_shape_and_log(caplog):
    caplog.set_level(logging.WARNING)
    r = TestClient(build()).get("/app-exc")
    assert r.status_code == 409
    assert r.json() == {
        "error": {
            "code": "email_already_registered",
            "message": "An account with this email already exists",
            "details": None,
        }
    }
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)


def test_unhandled_error_is_generic_and_logged(caplog):
    r = TestClient(build(), raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "hunter2" not in r.text
    assert any(rec.levelno == logging.ERROR and rec.exc_info for rec in caplog.records)


def test_validation_error_does_not_echo_input(caplog):
    r = TestClient(build()).post("/body", json={"password": "hunter2-secret", "n": "x"})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"][0]["field"] == "n"
    assert "hunter2-secret" not in r.text
    assert "hunter2-secret" not in caplog.text
