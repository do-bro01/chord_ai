"""SQLAlchemy 엔진/세션."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings

settings = get_settings()

# SQLite는 동일 커넥션을 여러 스레드에서 쓰지 않도록 기본 설정.
# FastAPI 의존성으로 요청마다 세션을 새로 만들기 때문에 안전하게 동작.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """앱 시작 시 테이블이 없으면 생성. v1은 Alembic 대신 단순 create_all."""
    # 모델을 임포트해 메타데이터에 등록
    from backend.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
