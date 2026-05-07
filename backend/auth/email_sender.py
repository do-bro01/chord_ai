"""SMTP를 통한 인증코드 메일 발송."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from backend.config import get_settings


class EmailSendError(RuntimeError):
    pass


def send_verification_email(to_email: str, code: str) -> None:
    settings = get_settings()
    if not settings.smtp_username or not settings.smtp_password:
        raise EmailSendError(
            "SMTP 환경변수(SMTP_USERNAME / SMTP_PASSWORD)가 설정되지 않았습니다."
        )

    msg = EmailMessage()
    msg["Subject"] = "[Chord AI] 이메일 인증코드"
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(
        "Chord AI 회원가입 인증코드입니다.\n\n"
        f"인증코드: {code}\n\n"
        "이 코드는 10분간 유효합니다.\n"
        "본인이 요청하지 않았다면 이 메일을 무시하세요."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    except Exception as e:
        raise EmailSendError(f"SMTP 발송 실패: {e}") from e
