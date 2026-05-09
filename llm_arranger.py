"""기능 3: OpenAI API 기반 편곡 요청

두 가지 인터페이스 제공:
  1. (신규) arrange_structured — 구조화 입력/출력 (PRD v2 메인 흐름)
  2. (레거시) arrange / confirm_and_arrange_interactive — 자유 텍스트 (CLI main.py 호환용)

신규 흐름 사용 예:
    from llm_arranger import (
        ArrangementInput, ArrangementOptions, arrange_structured
    )
    out = arrange_structured(ArrangementInput(
        current_chords=["C", "Am", "F", "G"],
        key="C major",
        options=ArrangementOptions(
            genre="Jazz", complexity="보통", tension="많음",
            bass_style="워킹 베이스", rhythm="싱코페이션",
        ),
        free_text="밤 드라이브 느낌",
    ))
    # out.chords, out.rationale, out.warnings
"""

from __future__ import annotations

import os
import re
from typing import List, Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

DEFAULT_MODEL = "gpt-4o"


# ============================================================================
# 신규: Structured I/O (PRD v2 메인 흐름)
# ============================================================================


GenreT = Literal["City Pop", "Jazz", "Ballad", "Lo-fi", "Bossa Nova"]
ComplexityT = Literal["단순", "보통", "복잡"]
TensionT = Literal["적음", "보통", "많음"]
BassStyleT = Literal["루트 중심", "부드러운 연결", "워킹 베이스"]
RhythmT = Literal["안정적", "싱코페이션", "펑키함"]


class ArrangementOptions(BaseModel):
    """5개 구조화 편곡 옵션."""
    genre: GenreT
    complexity: ComplexityT
    tension: TensionT
    bass_style: BassStyleT
    rhythm: RhythmT


class ArrangementInput(BaseModel):
    """편곡 요청 입력."""
    current_chords: List[str] = Field(..., description="원본 코드 진행 (한 칸에 한 마디)")
    key: str = Field(..., description="예: 'C major', 'A minor'")
    bpm: int = 100
    time_signature: str = "4/4"
    section_size_bars: int = Field(default=8, description="이 호출에서 편곡할 마디 수")
    options: ArrangementOptions
    free_text: Optional[str] = Field(default=None, description="분위기 보조 묘사")


class ArrangementOutput(BaseModel):
    """편곡 결과."""
    chords: List[str] = Field(..., description="편곡된 코드 진행 (마디별)")
    rationale: str = Field(..., description="어떤 변형을 했는지 1~2문장 한국어 설명")
    warnings: List[str] = Field(default_factory=list, description="옵션 충돌, 적용 못 한 옵션 등")


STRUCTURED_SYSTEM_PROMPT = """당신은 음악 이론에 능숙한 편곡가입니다.
사용자의 코드 진행과 구조화된 편곡 옵션을 받아, 옵션에 맞게 재구성된 코드 진행을 JSON으로 응답합니다.

## 옵션 의미

장르:
- City Pop: 7th/9th 텐션 풍부, II-V-I 흐름, 멜로딕한 베이스
- Jazz: 텐션 적극 활용, 트라이톤 대리·secondary dominant 빈번
- Ballad: 단순한 다이어토닉 위주, 감성적 진행
- Lo-fi: maj7/m7 위주 드림한 보이싱, 단순한 리듬
- Bossa Nova: 7th/9th + 슬래시 코드, 부드러운 보이싱

코드 복잡도:
- 단순: 트라이어드 위주
- 보통: 7th 코드 적극 사용
- 복잡: 9/11/13 텐션, 슬래시 코드, substitution 다수

텐션 사용량:
- 적음: 트라이어드 + 가끔 7th
- 보통: 7th 위주, 일부 9th
- 많음: 9/11/13 적극 사용

베이스 스타일:
- 루트 중심: 코드 루트만, slash 거의 없음
- 부드러운 연결: passing/slash 코드 사용 (예: C-G/B-Am)
- 워킹 베이스: 베이스가 경과음을 풍부하게 연결 (slash 코드 자주)

리듬 성향:
- 안정적: 코드 변경 빈도 낮음
- 싱코페이션: 코드 변경이 약박에 자주 옴
- 펑키함: 코드 stab + rest, 짧은 변경

## 출력 규칙

1. chords 배열의 길이는 **반드시 입력 current_chords의 길이와 정확히 동일**해야 한다.
   - 마디를 늘리거나 줄이지 마라.
   - 한 마디에 한 코드(한 항목). 한 마디를 두 코드로 쪼개거나 두 마디를 한 코드로 합치지 마라.
   - 표기는 music21 파싱 가능한 일반 표기.
   - 좋은 예: C, Cm, Cmaj7, Cm7, C7, C9, Cm9, Cmaj9, Cdim, Caug, Csus4, C/E, F#m7b5
   - 피할 표기: Cmaj9#11sus4, C(add9b13), 한글 표기, 마디 번호
2. 키 안에서 다이어토닉 + 적절한 borrowed chord(secondary dominant 등) 위주로 사용.
   완전한 키 이탈은 의도가 분명할 때만.
3. rationale: 1~2문장 한국어로 어떤 변형(reharmonization / tension / substitution / voice leading)을 했는지 설명.
4. warnings: 옵션 충돌(예: Lo-fi + 워킹 베이스 + 펑키함)이나 적용 못 한 옵션이 있으면 짧게 기록. 없으면 빈 리스트.
"""


class LLMArrangerError(RuntimeError):
    pass


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMArrangerError(
            "OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요."
        )
    return OpenAI(api_key=api_key)


def _format_user_message(req: ArrangementInput) -> str:
    n = len(req.current_chords)
    parts = [
        f"원본 코드 진행 ({n}마디): {' - '.join(req.current_chords)}",
        f"키: {req.key}",
        f"BPM: {req.bpm}",
        f"박자: {req.time_signature}",
        "",
        "편곡 옵션:",
        f"- 장르: {req.options.genre}",
        f"- 코드 복잡도: {req.options.complexity}",
        f"- 텐션 사용량: {req.options.tension}",
        f"- 베이스 스타일: {req.options.bass_style}",
        f"- 리듬 성향: {req.options.rhythm}",
    ]
    if req.free_text:
        parts.append(f"- 자유 묘사(보조): {req.free_text}")
    parts.append("")
    parts.append(
        f"위 옵션에 맞게 편곡된 코드 진행을 JSON으로 응답하세요. "
        f"chords 배열은 반드시 정확히 {n}개 항목이어야 합니다 "
        f"(원본과 같은 마디 수). 늘리거나 줄이지 마세요."
    )
    return "\n".join(parts)


def arrange_structured(
    req: ArrangementInput,
    model: str = DEFAULT_MODEL,
) -> ArrangementOutput:
    """구조화 입력 → 구조화 출력 편곡.

    OpenAI structured output(Pydantic 스키마 강제)을 사용해
    자유 텍스트 파싱을 제거하고 결과를 결정론적으로 받는다.

    LLM 출력의 음악적 타당성(키/표기 호환)은 별도로
    chord_postprocess의 검증 함수로 후처리해야 한다.
    """
    if not req.current_chords:
        raise LLMArrangerError("입력 코드 진행이 비어 있습니다.")

    client = _get_client()
    user_message = _format_user_message(req)

    try:
        completion = client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": STRUCTURED_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format=ArrangementOutput,
        )
    except Exception as e:
        raise LLMArrangerError(f"OpenAI structured parse 실패: {e}") from e

    if not completion.choices:
        raise LLMArrangerError("LLM 응답에 choices가 없습니다.")

    msg = completion.choices[0].message
    if msg.refusal:
        raise LLMArrangerError(f"LLM 거부 응답: {msg.refusal}")
    if msg.parsed is None:
        raise LLMArrangerError("LLM 응답을 ArrangementOutput으로 파싱하지 못했습니다.")
    return msg.parsed


# ============================================================================
# 레거시: 자유 텍스트 흐름 (기존 CLI main.py 호환용)
# ============================================================================


SYSTEM_PROMPT = """당신은 음악 이론에 능숙한 편곡가입니다.
사용자의 코드 진행과 원하는 분위기/스타일을 받아, 그 분위기에 맞게 편곡한 코드 진행을 제시합니다.

규칙:
1. 응답은 반드시 한 줄로 코드 진행만 출력합니다.
2. 코드는 하이픈(-)으로 구분하며, 공백을 함께 사용합니다. 예: "Am - F - C - G".
3. 마디 수는 입력 코드 진행과 비슷하게 유지합니다.
4. 사용 가능한 코드 표기: 메이저(C, D, E ...), 마이너(Cm, Dm ...), 7th(C7, Dm7 ...), 메이저7(Cmaj7), 디미니시드(Cdim), 어그멘티드(Caug), sus(Csus4) 등 일반적인 표기.
5. 코드 외 다른 설명, 마크다운, 주석은 출력하지 않습니다.
"""


CHORD_TOKEN_RE = re.compile(
    r"^[A-G](#|b)?(maj7|maj|min7|min|m7|m|sus2|sus4|dim7|dim|aug|7|6|9)?$"
)


def _parse_chords(text: str) -> List[str]:
    """LLM 응답에서 코드 토큰만 골라 리스트로 반환."""
    line = text.strip().splitlines()[0] if text.strip() else ""
    line = line.replace("`", "").strip()
    raw_tokens = re.split(r"\s*[-,/|]\s*|\s{2,}", line)
    chords: List[str] = []
    for tok in raw_tokens:
        tok = tok.strip()
        if not tok:
            continue
        if CHORD_TOKEN_RE.match(tok):
            chords.append(tok)
    if not chords:
        raise LLMArrangerError(
            f"LLM 응답에서 코드 진행을 인식하지 못했습니다. 원본 응답:\n{text}"
        )
    return chords


def arrange(
    chords: List[str],
    user_request: str,
    model: str = DEFAULT_MODEL,
) -> List[str]:
    """원본 코드 진행과 사용자 요청을 받아 편곡된 코드 진행을 반환."""
    if not chords:
        raise LLMArrangerError("입력 코드 진행이 비어 있습니다.")

    client = _get_client()
    user_message = (
        f"원본 코드 진행: {' - '.join(chords)}\n"
        f"편곡 요청: {user_request}\n"
        "위 요청에 맞게 편곡된 코드 진행을 한 줄로만 출력하세요."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as e:
        raise LLMArrangerError(f"OpenAI API 호출 실패: {e}") from e

    if not response.choices:
        raise LLMArrangerError("LLM 응답에 choices가 없습니다.")
    text = response.choices[0].message.content or ""
    if not text:
        raise LLMArrangerError("LLM 응답에 텍스트가 없습니다.")
    return _parse_chords(text)


def confirm_and_arrange_interactive(chords: List[str]) -> List[str] | None:
    """대화형 흐름: 편곡 여부 확인 → 사용자 요청 입력 → 편곡 결과 반환.

    사용자가 편곡을 원하지 않으면 None 반환.
    """
    print("\n편곡하시겠습니까? (y/n): ", end="", flush=True)
    answer = input().strip().lower()
    if answer not in {"y", "yes", "예", "ㅇ"}:
        return None

    print("어떤 느낌으로 편곡할까요? (예: '슬픈 느낌의 기타 솔로로 편곡해줘'): ", end="", flush=True)
    user_request = input().strip()
    if not user_request:
        raise LLMArrangerError("편곡 요청이 비어 있습니다.")

    print("\n[OpenAI API] 편곡 요청 중...")
    arranged = arrange(chords, user_request)
    return arranged
