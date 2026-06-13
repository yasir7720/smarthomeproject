import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(encrypted: str | None) -> str | None:
    if not encrypted:
        return None
    if encrypted.startswith("enc::"):
        return encrypted[5:]
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None
