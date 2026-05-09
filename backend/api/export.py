"""Export 라우트.

코드 진행을 MusicXML / MIDI / PDF 파일로 변환해 즉시 다운로드 응답으로 반환.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from audio_renderer import build_midi
from backend.auth.deps import get_current_user
from backend.db.models import User
from score_generator import _build_score, _configure_musescore

router = APIRouter(prefix="/api/export", tags=["export"])
log = logging.getLogger("chord_ai.export")

MAX_BARS = 256

FormatT = Literal["musicxml", "midi", "pdf"]

_MEDIA_TYPE = {
    "musicxml": "application/vnd.recordare.musicxml+xml",
    "midi": "audio/midi",
    "pdf": "application/pdf",
}
_EXT = {"musicxml": "musicxml", "midi": "mid", "pdf": "pdf"}


class ExportIn(BaseModel):
    chords: list[str] = Field(..., description="마디별 코드 라벨")
    format: FormatT
    bpm: int = Field(default=100, ge=40, le=240)
    beats_per_bar: int = Field(default=4, ge=1, le=12)
    title: str = Field(default="Arranged", max_length=80)


def _slugify_filename(title: str, ext: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title).strip() or "Arranged"
    return f"{safe}.{ext}"


def _midi_bytes(req: ExportIn) -> bytes:
    pm = build_midi(req.chords, bpm=req.bpm, beats_per_bar=req.beats_per_bar)
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        pm.write(str(tmp_path))
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def _musicxml_bytes(req: ExportIn) -> bytes:
    score = _build_score(req.chords, title=req.title)
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        score.write("musicxml", fp=str(tmp_path))
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def _pdf_bytes(req: ExportIn) -> bytes:
    if _configure_musescore() is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MUSESCORE_MISSING",
                "message": "PDF 변환에 필요한 MuseScore가 설치되지 않았습니다.",
            },
        )
    score = _build_score(req.chords, title=req.title)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        score.write("musicxml.pdf", fp=str(tmp_path))
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post(
    "",
    responses={
        200: {
            "content": {
                "application/vnd.recordare.musicxml+xml": {},
                "audio/midi": {},
                "application/pdf": {},
            }
        }
    },
)
def export_endpoint(
    req: ExportIn,
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
                "message": f"export는 최대 {MAX_BARS}마디까지 지원합니다.",
            },
        )

    try:
        if req.format == "midi":
            data = _midi_bytes(req)
        elif req.format == "musicxml":
            data = _musicxml_bytes(req)
        elif req.format == "pdf":
            data = _pdf_bytes(req)
        else:  # 방어적 — Literal로 막혀있어 도달 안 함
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_FORMAT", "message": f"지원하지 않는 포맷: {req.format}"},
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("export failed: format=%s", req.format)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EXPORT_FAILED", "message": "export 생성 중 오류가 발생했습니다."},
        ) from e

    filename = _slugify_filename(req.title, _EXT[req.format])
    return Response(
        content=data,
        media_type=_MEDIA_TYPE[req.format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
