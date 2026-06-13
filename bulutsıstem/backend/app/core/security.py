import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlparse, urlunparse

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_stream_token(user_id: uuid.UUID, tenant_id: uuid.UUID, stream_key: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.stream_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "stream_key": stream_key,
        "exp": expire,
        "type": "stream",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None


def decode_stream_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "stream":
            return None
        return {
            "user_id": uuid.UUID(payload["sub"]),
            "tenant_id": uuid.UUID(payload["tenant_id"]),
            "stream_key": payload["stream_key"],
        }
    except (JWTError, ValueError, KeyError):
        return None


def generate_stream_key() -> str:
    return secrets.token_urlsafe(16)


def generate_tenant_slug(email: str) -> str:
    base = email.split("@")[0].lower().replace(".", "-")[:20]
    suffix = secrets.token_hex(3)
    return f"{base}-{suffix}"


def generate_mqtt_password() -> str:
    return secrets.token_urlsafe(24)


def generate_edge_agent_key() -> str:
    return secrets.token_urlsafe(32)


def encrypt_camera_password(password: str | None) -> str | None:
    from app.core.encryption import encrypt_secret

    return encrypt_secret(password)


def decrypt_camera_password(encrypted: str | None) -> str | None:
    from app.core.encryption import decrypt_secret

    return decrypt_secret(encrypted)


def build_authenticated_stream_url(
    stream_url: str, username: str | None, password: str | None
) -> str:
    if not username or not password:
        return stream_url
    parsed = urlparse(stream_url)
    if parsed.scheme not in ("rtsp", "http", "https"):
        return stream_url
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{quote(username)}:{quote(password)}@{host}{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
