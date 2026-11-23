import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.auth.encryption import decrypt_token, encrypt_token


def test_round_trip():
    blob = encrypt_token("access-sandbox-abc")
    assert isinstance(blob, bytes)
    assert decrypt_token(blob) == "access-sandbox-abc"


def test_ciphertext_hides_the_token_and_differs_each_time():
    a, b = encrypt_token("access-sandbox-abc"), encrypt_token("access-sandbox-abc")
    assert b"access-sandbox-abc" not in a
    assert a != b


def test_a_different_key_cannot_decrypt():
    foreign = Fernet(Fernet.generate_key()).encrypt(b"access-sandbox-abc")
    with pytest.raises(InvalidToken):
        decrypt_token(foreign)


def test_tampered_ciphertext_is_rejected():
    blob = bytearray(encrypt_token("access-sandbox-abc"))
    blob[-5] ^= 1
    with pytest.raises(InvalidToken):
        decrypt_token(bytes(blob))
