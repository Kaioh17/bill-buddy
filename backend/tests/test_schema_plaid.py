import pytest
from pydantic import ValidationError

from app.schema.plaid import ExchangeRequest


def test_exchange_request_trims_the_institution_name():
    r = ExchangeRequest(public_token="public-1", institution_name="  Chase  ")
    assert r.institution_name == "Chase"


@pytest.mark.parametrize(
    "bad",
    [
        {"institution_name": "Chase"},
        {"public_token": "", "institution_name": "Chase"},
        {"public_token": "public-1"},
        {"public_token": "public-1", "institution_name": "   "},
        {"public_token": "public-1", "institution_name": "x" * 101},
        {"public_token": "p" * 501, "institution_name": "Chase"},
        {"public_token": "public-1", "institution_name": "Chase", "user_id": "abc"},
    ],
)
def test_exchange_request_rejects_bad_input(bad):
    with pytest.raises(ValidationError):
        ExchangeRequest(**bad)
