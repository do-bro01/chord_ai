"""비밀번호 해싱 + JWT 발급/검증."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from backend.config import get_settings

_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """bcrypt로 비밀번호 해싱."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def hash_code(code: str) -> str:
    """인증코드도 평문 저장 금지 → bcrypt 해시."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(code.encode("utf-8"), salt).decode("utf-8")


def verify_code(code: str, code_hash: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), code_hash.encode("utf-8"))
    except Exception:
        return False


def generate_numeric_code(length: int = 6) -> str:
    """secrets로 6자리 숫자 코드 생성."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_state_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def create_access_token(user_id: str, email: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_expire_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
