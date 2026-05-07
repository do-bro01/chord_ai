"""인증 라우트."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.auth import google, service
from backend.auth.deps import get_current_user
from backend.auth.email_sender import EmailSendError, send_verification_email
from backend.auth.schemas import (
    LoginIn,
    SignupRequestCodeIn,
    SignupVerifyIn,
    UserOut,
)
from backend.auth.security import create_access_token, generate_state_token
from backend.config import get_settings
from backend.db.database import get_db
from backend.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "chord_ai_oauth_state"
log = logging.getLogger("chord_ai.auth")


def _set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    token = create_access_token(user.id, user.email)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        provider=user.provider,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
    )


def _raise_auth(error: service.AuthError) -> None:
    raise HTTPException(
        status_code=error.http_status,
        detail={"code": error.code, "message": error.message},
    )


# ---------- 회원가입 ----------

@router.post("/signup/request-code", status_code=status.HTTP_204_NO_CONTENT)
def signup_request_code(payload: SignupRequestCodeIn, db: Session = Depends(get_db)) -> Response:
    """이메일로 6자리 인증코드 발송. 가입 여부와 무관하게 동일 응답."""
    # 이미 가입된 이메일이면 발송하지 않고 정상 응답 (정보 노출 방지)
    existing = service.get_user_by_email(db, payload.email)
    if existing is not None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        code, _ = service.issue_signup_code(db, payload.email)
    except service.AuthError as e:
        _raise_auth(e)

    try:
        send_verification_email(payload.email, code)
    except EmailSendError as e:
        log.exception("SMTP 발송 실패")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "EMAIL_SEND_FAILED", "message": "메일 발송에 실패했습니다. 잠시 후 다시 시도하세요."},
        ) from e

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/signup/verify", response_model=UserOut)
def signup_verify(
    payload: SignupVerifyIn,
    response: Response,
    db: Session = Depends(get_db),
) -> UserOut:
    try:
        user = service.verify_signup(db, payload.email, payload.code, payload.password)
    except service.AuthError as e:
        _raise_auth(e)

    _set_session_cookie(response, user)
    return _user_out(user)


# ---------- 로그인/로그아웃/me ----------

@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    try:
        user = service.login(db, payload.email, payload.password)
    except service.AuthError as e:
        _raise_auth(e)
    _set_session_cookie(response, user)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    # 쿠키 삭제 헤더는 실제로 반환되는 Response에 직접 설정해야 한다.
    # response: Response 의존성에 set 해놓고 새 Response를 return하면 헤더가 유실된다.
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)


# ---------- Google OAuth ----------

@router.get("/google/start")
def google_start() -> RedirectResponse:
    state = generate_state_token()
    try:
        url = google.build_authorize_url(state)
    except google.GoogleOAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "OAUTH_NOT_CONFIGURED", "message": str(e)},
        ) from e

    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    settings = get_settings()
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/auth/google",
    )
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    chord_ai_oauth_state: str | None = Cookie(default=None),
) -> RedirectResponse:
    settings = get_settings()
    frontend = settings.frontend_origin

    if error:
        return RedirectResponse(url=f"{frontend}/login?error=oauth_denied", status_code=302)
    if not code or not state:
        return RedirectResponse(url=f"{frontend}/login?error=oauth_invalid", status_code=302)
    if not chord_ai_oauth_state or state != chord_ai_oauth_state:
        return RedirectResponse(url=f"{frontend}/login?error=oauth_state_mismatch", status_code=302)

    try:
        token_resp = google.exchange_code(code)
        id_token_value = token_resp.get("id_token")
        if not id_token_value:
            raise google.GoogleOAuthError("id_token이 응답에 없습니다.")
        gu = google.verify_id_token(id_token_value)
    except google.GoogleOAuthError:
        log.exception("Google OAuth 처리 실패")
        return RedirectResponse(url=f"{frontend}/login?error=oauth_failed", status_code=302)

    user = service.upsert_google_user(db, gu.email, gu.sub)

    response = RedirectResponse(url=f"{frontend}/", status_code=302)
    _set_session_cookie(response, user)
    # state 쿠키 정리
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        path="/auth/google",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return response
