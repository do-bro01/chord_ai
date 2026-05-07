"""Google OAuth 2.0 (Authorization Code Flow) 헬퍼."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from backend.config import get_settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = "openid email profile"


class GoogleOAuthError(RuntimeError):
    pass


@dataclass(slots=True)
class GoogleUser:
    sub: str
    email: str
    email_verified: bool


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    if not settings.google_client_id:
        raise GoogleOAuthError("GOOGLE_CLIENT_ID 환경변수가 설정되지 않았습니다.")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """authorization code → access_token + id_token."""
    settings = get_settings()
    if not settings.google_client_secret:
        raise GoogleOAuthError("GOOGLE_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(GOOGLE_TOKEN_URL, data=data)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        raise GoogleOAuthError(f"토큰 교환 실패: {e}") from e


def verify_id_token(token: str) -> GoogleUser:
    """id_token 서명/issuer/aud 검증 후 사용자 정보 반환."""
    settings = get_settings()
    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except Exception as e:
        raise GoogleOAuthError(f"id_token 검증 실패: {e}") from e

    sub = claims.get("sub")
    email = claims.get("email")
    if not sub or not email:
        raise GoogleOAuthError("id_token에 sub/email이 없습니다.")

    return GoogleUser(
        sub=sub,
        email=email.lower(),
        email_verified=bool(claims.get("email_verified", False)),
    )
