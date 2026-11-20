import pytest
from pydantic import ValidationError

from app.schema.auth import (
    EMAIL_MAX,
    NAME_MAX,
    PASSWORD_MAX,
    PASSWORD_MIN,
    LoginRequest,
    SignupRequest,
)
from tests.conftest import GOOD_SIGNUP


def signup(**over):
    return SignupRequest(**{**GOOD_SIGNUP, **over})


def pw(n):
    return "p" * n


def test_valid_signup_normalises_input():
    s = signup(email="  Ada@Example.COM ", first_name="  Ada ", last_name=" Lovelace  ")
    assert s.email == "ada@example.com"
    assert (s.first_name, s.last_name) == ("Ada", "Lovelace")


@pytest.mark.parametrize(
    "n,ok",
    [
        (PASSWORD_MIN - 1, False),
        (PASSWORD_MIN, True),
        (PASSWORD_MAX, True),
        (PASSWORD_MAX + 1, False),
    ],
)
def test_password_length_boundaries(n, ok):
    if ok:
        signup(password=pw(n), confirm_password=pw(n))
    else:
        with pytest.raises(ValidationError):
            signup(password=pw(n), confirm_password=pw(n))


def test_passwords_must_match():
    with pytest.raises(ValidationError, match="do not match"):
        signup(confirm_password="something else entirely")


def test_password_is_not_trimmed():
    s = signup(password="  spaces are fine  ", confirm_password="  spaces are fine  ")
    assert s.password == "  spaces are fine  "


def test_email_length_limit():
    long_email = "a" * (EMAIL_MAX - len("@example.com") + 1) + "@example.com"
    assert len(long_email) == EMAIL_MAX + 1
    with pytest.raises(ValidationError):
        signup(email=long_email)


def test_huge_email_rejected_cheaply():
    with pytest.raises(ValidationError):
        signup(email="a" * 100_000 + "@example.com")


def test_bad_email_rejected():
    with pytest.raises(ValidationError):
        signup(email="not-an-email")


@pytest.mark.parametrize("field", ["first_name", "last_name"])
def test_name_limits(field):
    signup(**{field: "x" * NAME_MAX})
    for bad in ("", "   ", "x" * (NAME_MAX + 1)):
        with pytest.raises(ValidationError):
            signup(**{field: bad})


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        signup(is_admin=True)


def test_login_normalises_email_and_bounds_password():
    assert (
        LoginRequest(email=" Ada@Example.com", password="x").email == "ada@example.com"
    )
    with pytest.raises(ValidationError):
        LoginRequest(email="ada@example.com", password="")
    with pytest.raises(ValidationError):
        LoginRequest(email="ada@example.com", password=pw(PASSWORD_MAX + 1))
