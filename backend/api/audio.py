"""오디오 분석 라우트.

업로드된 음원을 임시 파일로 저장한 뒤 audio_analysis.analyze 로
코드 진행을 추출해 반환한다.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.auth.deps import get_current_user
from backend.db.models import User

router = APIRouter(prefix="/api/audio", tags=["audio"])
log = logging.getLogger("chord_ai.audio")

SUPPORTED_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class ExtractOut(BaseModel):
    filename: str
    chords: list[str]


def _suffix_from_filename(name: str) -> str:
    s = Path(name).suffix.lower()
    return s


@router.post("/extract", response_model=ExtractOut)
async def extract_chords(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> ExtractOut:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_FILE", "message": "파일이 비어 있습니다."},
        )

    suffix = _suffix_from_filename(file.filename)
    if suffix not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_FORMAT",
                "message": f"지원하지 않는 형식입니다: {suffix or '확장자 없음'}",
            },
        )

    # 임시 파일에 스트리밍 저장 (메모리 절약, 사이즈 제한 적용)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        size = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                tmp.close()
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "code": "FILE_TOO_LARGE",
                        "message": "파일이 너무 큽니다. 50MB 이하로 업로드해주세요.",
                    },
                )
            tmp.write(chunk)

    try:
        # demucs/autochord/tensorflow는 import 비용이 매우 커서 요청 시점에 늦게 로드한다.
        # 첫 호출에서는 모델 가중치 다운로드(htdemucs ~80MB)도 발생할 수 있다.
        from audio_analysis import analyze  # type: ignore

        chords = analyze(tmp_path)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "AUDIO_INVALID", "message": str(e)},
        ) from e
    except Exception as e:
        log.exception("코드 추출 실패")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EXTRACT_FAILED",
                "message": "코드 추출 중 오류가 발생했습니다.",
            },
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    if not chords:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "NO_CHORDS",
                "message": "코드 진행을 추출하지 못했습니다. 다른 음원을 시도해주세요.",
            },
        )

    return ExtractOut(filename=file.filename, chords=chords)
