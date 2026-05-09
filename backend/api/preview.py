"""미리듣기 라우트.

코드 진행 + BPM/박자를 받아 피아노 1트랙 MIDI를 합성한 WAV를
즉시 audio/wav 응답으로 반환한다 (디스크 저장 없음).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from audio_renderer import render_to_bytes
from backend.auth.deps import get_current_user
from backend.db.models import User

router = APIRouter(prefix="/api/preview", tags=["preview"])
log = logging.getLogger("chord_ai.preview")

MAX_BARS = 64  # 1마디 = ~2~3초이므로 64마디면 최대 ~3분


class PreviewIn(BaseModel):
    chords: list[str] = Field(..., description="마디별 코드 라벨")
    bpm: int = Field(default=100, ge=40, le=240)
    beats_per_bar: int = Field(default=4, ge=1, le=12)


@router.post("", responses={200: {"content": {"audio/wav": {}}}})
def preview_endpoint(
    req: PreviewIn,
    _: User = Depends(get_current_user),
) -> Response:
    if not req.chords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_CHORDS", "message": "코드 진행이 비어 있습니다."},
        )
    if len(req.chords) > MAX_BARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOO_MANY_BARS",
                "message": f"미리듣기는 최대 {MAX_BARS}마디까지 지원합니다.",
            },
        )

    try:
        wav = render_to_bytes(
            req.chords,
            bpm=req.bpm,
            beats_per_bar=req.beats_per_bar,
        )
    except FileNotFoundError as e:
        log.error("soundfont missing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SOUNDFONT_MISSING", "message": str(e)},
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": str(e)},
        ) from e
    except Exception as e:
        log.exception("preview render failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RENDER_FAILED", "message": "미리듣기 생성 실패"},
        ) from e

    return Response(content=wav, media_type="audio/wav")
