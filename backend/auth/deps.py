"""FastAPI 의존성: 현재 사용자."""

from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.security import decode_access_token
from backend.config import get_settings
from backend.db.database import get_db
from backend.db.models import User


def get_current_user(
    db: Session = Depends(get_db),
    chord_ai_session: str | None = Cookie(default=None),
) -> User:
    settings = get_settings()
    if chord_ai_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "NOT_AUTHENTICATED", "message": "로그인이 필요합니다."},
        )
    try:
        payload = decode_access_token(chord_ai_session)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "세션이 만료되었거나 유효하지 않습니다."},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "세션 정보가 올바르지 않습니다."},
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "사용자를 찾을 수 없습니다."},
        )

    # settings는 의존성 캐시 측면에서 함수 내에서 한 번만 호출
    _ = settings
    return user
