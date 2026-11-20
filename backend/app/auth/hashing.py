"""Password hashing with argon2id. Hashes only, nothing here can recover a password."""

from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# argon2-cffi defaults follow the RFC 9106 recommended profile and embed the
# parameters and a random salt in each hash string.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


@cache
def _dummy_hash() -> str:
    return _hasher.hash("dummy-password-for-timing")


def verify_password(password: str, hashed: str | None) -> bool:
    """True if password matches. A None hash (unknown user) still costs one full
    verification, so response time does not reveal whether an email exists."""
    try:
        return _hasher.verify(hashed or _dummy_hash(), password) and hashed is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if the hash used weaker parameters than the current settings."""
    return _hasher.check_needs_rehash(hashed)
