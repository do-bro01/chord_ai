"""편곡 라우트.

Song(파트 + 흐름)과 키/장르/자유 묘사를 받아 LLM 구조화 편곡을 실행한다.

함수 보존 검증 + 재시도 루프는 Phase 1.2에서 추가 예정 (현재는 LLM 응답을 그대로 반환).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth.deps import get_current_user
from backend.db.models import User
from llm_arranger import (
    ArrangementInput,
    LLMArrangerError,
    Part,
    arrange_structured,
)

router = APIRouter(prefix="/api/arrange", tags=["arrange"])
log = logging.getLogger("chord_ai.arrange")


class ArrangeOut(BaseModel):
    parts: list[Part] = Field(
        ...,
        description="편곡된 파트 목록. 입력 song.parts와 1:1 대응 (이름·마디 수·각 마디 코드 수 동일).",
    )
    structure: list[str] | None = Field(
        default=None,
        description="입력 song.structure 그대로 echo. 곡 흐름.",
    )
    rationale: str
    warnings: list[str]


@router.post("", response_model=ArrangeOut)
def arrange_endpoint(
    req: ArrangementInput,
    _: User = Depends(get_current_user),
) -> ArrangeOut:
    if not req.song.parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_SONG", "message": "song.parts가 비어 있습니다."},
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

    return ArrangeOut(
        parts=out.parts,
        structure=req.song.structure,
        rationale=out.rationale,
        warnings=out.warnings,
    )
