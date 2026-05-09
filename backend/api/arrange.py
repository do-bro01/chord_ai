"""편곡 라우트.

코드 진행 + 구조화 옵션을 받아 LLM 구조화 편곡을 실행하고,
룰 베이스 검증 리포트와 함께 반환한다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth.deps import get_current_user
from backend.db.models import User
from chord_postprocess import parse_key_string, validate_arrangement
from llm_arranger import (
    ArrangementInput,
    LLMArrangerError,
    arrange_structured,
)

router = APIRouter(prefix="/api/arrange", tags=["arrange"])
log = logging.getLogger("chord_ai.arrange")


class ChordValidationOut(BaseModel):
    label: str
    normalized: str
    music21_ok: bool
    membership: str
    issue: str | None


class ValidationReportOut(BaseModel):
    foreign_count: int
    unparseable_count: int
    music21_failures: list[str]
    has_issues: bool
    chords: list[ChordValidationOut]


class ArrangeOut(BaseModel):
    chords: list[str] = Field(..., description="LLM 편곡 원본 라벨 (정규화 전)")
    rationale: str
    warnings: list[str]
    validation: ValidationReportOut


@router.post("", response_model=ArrangeOut)
def arrange_endpoint(
    req: ArrangementInput,
    _: User = Depends(get_current_user),
) -> ArrangeOut:
    if not req.current_chords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_CHORDS", "message": "코드 진행이 비어 있습니다."},
        )

    try:
        out = arrange_structured(req)
    except LLMArrangerError as e:
        log.warning("LLM arrange failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "LLM_FAILED", "message": str(e)},
        ) from e
    except Exception as e:
        log.exception("LLM arrange unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ARRANGE_FAILED", "message": "편곡 중 오류가 발생했습니다."},
        ) from e

    root, mode = parse_key_string(req.key)
    report = validate_arrangement(out.chords, root, mode)

    return ArrangeOut(
        chords=out.chords,
        rationale=out.rationale,
        warnings=out.warnings,
        validation=ValidationReportOut(
            foreign_count=report.foreign_count,
            unparseable_count=report.unparseable_count,
            music21_failures=report.music21_failures,
            has_issues=report.has_issues,
            chords=[
                ChordValidationOut(
                    label=c.label,
                    normalized=c.normalized,
                    music21_ok=c.music21_ok,
                    membership=c.membership,
                    issue=c.issue,
                )
                for c in report.chords
            ],
        ),
    )
