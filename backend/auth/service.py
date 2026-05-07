"""인증 비즈니스 로직."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.security import (
    generate_numeric_code,
    hash_code,
    hash_password,
    verify_code,
    verify_password,
)
from backend.db.models import EmailVerification, User

CODE_TTL_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60
MAX_VERIFY_ATTEMPTS = 5

PASSWORD_MIN_LEN = 8
PASSWORD_MAX_LEN = 72


class AuthError(Exception):
    """인증 비즈니스 오류. (code, http_status, message)"""

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LEN or len(password) > PASSWORD_MAX_LEN:
        raise AuthError("WEAK_PASSWORD", "비밀번호는 8자 이상 72자 이하여야 합니다.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AuthError(
            "WEAK_PASSWORD",
            "비밀번호는 영문과 숫자를 모두 포함해야 합니다.",
        )


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


# ---------- 회원가입: 인증코드 발급 ----------

def issue_signup_code(db: Session, email: str) -> tuple[str, bool]:
    """인증코드 발급. (생성된 평문코드, 신규발급여부) 반환.

    이미 가입된 이메일이라도 동일하게 동작 (정보 노출 방지).
    재발송 쿨다운 60초 적용.
    """
    email_n = _normalize_email(email)

    # 쿨다운: 같은 email+purpose에서 가장 최근 미소비 레코드 확인
    latest = db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.email == email_n,
            EmailVerification.purpose == "signup",
            EmailVerification.consumed_at.is_(None),
        )
        .order_by(EmailVerification.created_at.desc())
    )
    if latest:
        elapsed = (_now() - _ensure_aware(latest.created_at)).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            raise AuthError(
                "RATE_LIMITED",
                f"잠시 후 다시 시도하세요. ({int(RESEND_COOLDOWN_SECONDS - elapsed)}초)",
                http_status=429,
            )
        # 미소비 기존 레코드 무효화
        latest.consumed_at = _now()

    code = generate_numeric_code(6)
    record = EmailVerification(
        email=email_n,
        code_hash=hash_code(code),
        purpose="signup",
        expires_at=_now() + timedelta(minutes=CODE_TTL_MINUTES),
    )
    db.add(record)
    db.commit()
    return code, True


# ---------- 회원가입: 검증 + 사용자 생성 ----------

def verify_signup(db: Session, email: str, code: str, password: str) -> User:
    email_n = _normalize_email(email)
    validate_password(password)

    if get_user_by_email(db, email_n) is not None:
        raise AuthError("EMAIL_TAKEN", "이미 가입된 이메일입니다.", http_status=409)

    record = db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.email == email_n,
            EmailVerification.purpose == "signup",
            EmailVerification.consumed_at.is_(None),
        )
        .order_by(EmailVerification.created_at.desc())
    )
    if record is None:
        raise AuthError("CODE_INVALID", "인증코드를 다시 요청하세요.", http_status=400)

    if _ensure_aware(record.expires_at) < _now():
        record.consumed_at = _now()
        db.commit()
        raise AuthError("CODE_EXPIRED", "인증코드가 만료되었습니다.", http_status=400)

    if record.attempts >= MAX_VERIFY_ATTEMPTS:
        record.consumed_at = _now()
        db.commit()
        raise AuthError(
            "CODE_TOO_MANY_ATTEMPTS",
            "시도 횟수를 초과했습니다. 인증코드를 다시 요청하세요.",
            http_status=400,
        )

    if not verify_code(code, record.code_hash):
        record.attempts += 1
        db.commit()
        raise AuthError("CODE_INVALID", "인증코드가 올바르지 않습니다.", http_status=400)

    # 코드 소비 + 사용자 생성
    record.consumed_at = _now()
    user = User(
        email=email_n,
        password_hash=hash_password(password),
        provider="email",
        email_verified_at=_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------- 로그인 ----------

def login(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not user.password_hash:
        raise AuthError("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.", http_status=401)
    if not verify_password(password, user.password_hash):
        raise AuthError("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.", http_status=401)
    return user


# ---------- Google OAuth: 사용자 upsert ----------

def upsert_google_user(db: Session, email: str, sub: str) -> User:
    email_n = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == email_n))
    if user is None:
        user = User(
            email=email_n,
            provider="google",
            provider_subject=sub,
            email_verified_at=_now(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # 기존 이메일 계정에 Google 연결
    if not user.provider_subject:
        user.provider_subject = sub
    if not user.email_verified_at:
        user.email_verified_at = _now()
    db.commit()
    db.refresh(user)
    return user


# ---------- 유틸 ----------

def _ensure_aware(dt: datetime) -> datetime:
    """SQLite는 timezone 정보를 잃을 수 있어 UTC로 강제."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
