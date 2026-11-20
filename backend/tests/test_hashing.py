from argon2 import PasswordHasher

from app.auth.hashing import hash_password, needs_rehash, verify_password


def test_hash_is_argon2id_and_not_plaintext():
    h = hash_password("correct horse battery")
    assert h.startswith("$argon2id$")
    assert "correct horse" not in h


def test_same_password_hashes_differently():
    assert hash_password("same-password-123") != hash_password("same-password-123")


def test_verify_correct_and_wrong():
    h = hash_password("correct horse battery")
    assert verify_password("correct horse battery", h) is True
    assert verify_password("wrong horse battery", h) is False


def test_verify_missing_hash_is_false():
    # Unknown user path: still does the work, never succeeds.
    assert verify_password("anything", None) is False


def test_verify_garbage_hash_is_false():
    assert verify_password("anything", "not-a-hash") is False


def test_needs_rehash():
    assert needs_rehash(hash_password("correct horse battery")) is False
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash("x")
    assert needs_rehash(weak) is True
