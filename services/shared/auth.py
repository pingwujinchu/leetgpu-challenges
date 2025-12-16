from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.hash import pbkdf2_sha256

try:
    import bcrypt as bcrypt_lib  # type: ignore
except Exception:  # pragma: no cover
    bcrypt_lib = None


def hash_password(password: str) -> str:
    # Use pbkdf2_sha256 to avoid passlib<->bcrypt backend/version issues and the 72-byte limit.
    return pbkdf2_sha256.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    # Preferred: pbkdf2_sha256 hashes.
    if password_hash.startswith("$pbkdf2-sha256$"):
        return pbkdf2_sha256.verify(password, password_hash)

    # Backwards compatibility: verify bcrypt hashes without passlib's bcrypt backend.
    # (passlib's bcrypt backend can break depending on installed bcrypt version)
    if password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        if bcrypt_lib is None:
            return False
        try:
            pw = password.encode("utf-8")[:72]  # bcrypt truncates at 72 bytes
            return bcrypt_lib.checkpw(pw, password_hash.encode("utf-8"))
        except Exception:
            return False

    return False


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str,
    expires_minutes: int,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError as e:
        raise ValueError(str(e)) from e

