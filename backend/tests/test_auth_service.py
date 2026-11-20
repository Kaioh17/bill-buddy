import logging

import pytest

from app.auth.hashing import verify_password
from app.auth.tokens import decode_token
from app.core.exception import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.schema.auth import LoginRequest, SignupRequest
from app.services import auth as service
from tests.conftest import GOOD_SIGNUP

pytestmark = pytest.mark.anyio


async def test_signup_stores_argon2_hash_not_password(fake_db):
    user = await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))
    assert user.email == "ada@example.com"
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(GOOD_SIGNUP["password"], user.password_hash)
    assert user.id is not None


async def test_signup_duplicate_email_conflicts(fake_db):
    await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))
    with pytest.raises(EmailAlreadyRegisteredError):
        await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))


async def test_signup_race_on_unique_index_becomes_conflict(fake_db):
    fake_db.race = True  # precheck passes, insert hits the unique constraint
    with pytest.raises(EmailAlreadyRegisteredError):
        await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))
    assert fake_db.rollbacks == 1


async def test_login_returns_decodable_token(fake_db):
    user = await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))
    token = await service.login(
        fake_db, LoginRequest(email="ada@example.com", password=GOOD_SIGNUP["password"])
    )
    assert token.token_type == "bearer"
    assert token.expires_in == 15 * 60
    assert decode_token(token.access_token).sub == str(user.id)


async def test_login_wrong_password_and_unknown_email_look_identical(fake_db):
    await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))
    errors = []
    for email, pw in [
        ("ada@example.com", "wrong password here"),
        ("nobody@example.com", "whatever"),
    ]:
        with pytest.raises(InvalidCredentialsError) as e:
            await service.login(fake_db, LoginRequest(email=email, password=pw))
        errors.append((e.value.code, e.value.message))
    assert errors[0] == errors[1]


async def test_login_unknown_email_still_runs_a_hash_verify(fake_db, monkeypatch):
    calls = []
    real = service.verify_password
    monkeypatch.setattr(
        service, "verify_password", lambda p, h: calls.append(h) or real(p, h)
    )
    with pytest.raises(InvalidCredentialsError):
        await service.login(
            fake_db, LoginRequest(email="nobody@example.com", password="x")
        )
    assert calls == [None]


async def test_events_logged_without_secrets(fake_db, caplog):
    caplog.set_level(logging.DEBUG)
    await service.signup(fake_db, SignupRequest(**GOOD_SIGNUP))
    await service.login(
        fake_db, LoginRequest(email="ada@example.com", password=GOOD_SIGNUP["password"])
    )
    with pytest.raises(InvalidCredentialsError):
        await service.login(
            fake_db, LoginRequest(email="ada@example.com", password="bad password!!")
        )
    msgs = [r.getMessage() for r in caplog.records]
    assert {"signup_ok", "login_ok", "login_failed"} <= set(msgs)
    assert GOOD_SIGNUP["password"] not in caplog.text
    assert "bad password!!" not in caplog.text
    # only the masked email may appear, in the message or any structured field
    assert all("ada@example.com" not in str(r.__dict__) for r in caplog.records)
