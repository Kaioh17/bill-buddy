"""Encrypts Plaid access tokens before they are saved (Fernet: AES-128-CBC + HMAC).

The key is TOKEN_ENCRYPTION_KEY. Decrypting with another key or tampered data raises
cryptography.fernet.InvalidToken.
"""

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().token_encryption_key.get_secret_value())


def encrypt_token(plain: str) -> bytes:
    return _fernet().encrypt(plain.encode())


def decrypt_token(blob: bytes) -> str:
    return _fernet().decrypt(blob).decode()
