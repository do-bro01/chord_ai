"""Pydantic 요청/응답 모델."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequestCodeIn(BaseModel):
    email: EmailStr


class SignupVerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    id: str
    email: str
    provider: str
    email_verified_at: datetime | None
    created_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
