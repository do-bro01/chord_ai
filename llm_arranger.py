"""기능 3: OpenAI API 기반 편곡 요청

두 가지 인터페이스 제공:
  1. (신규) arrange_structured — Song(파트+구조) 기반 구조화 I/O
  2. (레거시) arrange / confirm_and_arrange_interactive — 자유 텍스트 (CLI main.py 호환용)

신규 흐름 사용 예:
    from llm_arranger import (
        ArrangementInput, Song, Part, Bar, arrange_structured,
    )
    song = Song(
        parts=[
            Part(name="Intro", bars=[Bar(chords=["G"]), Bar(chords=["CM7"])]),
            Part(name="Verse", bars=[
                Bar(chords=["G", "CM7"]),
                Bar(chords=["Bm7", "E7#5", "E7"]),
                Bar(chords=["Am9", "C/D", "D7"]),
                Bar(chords=["Gsus4", "G"]),
            ]),
        ],
        structure=["Intro", "Verse", "Verse"],
    )
    out = arrange_structured(ArrangementInput(
        song=song, key="G major", bpm=82,
        genre="City Pop", free_text="밤 드라이브 느낌",
    ))
    # out.parts (편곡된 파트들), out.rationale, out.warnings
"""

from __future__ import annotations

import os
import re
from typing import List, Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from chord_postprocess import function_table_text

load_dotenv()

DEFAULT_MODEL = "gpt-4o"


# ============================================================================
# 신규: Structured I/O — Song(parts + structure) 기반
# ============================================================================


GenreT = Literal["City Pop", "Jazz", "Ballad", "Lo-fi", "Bossa Nova"]


class Bar(BaseModel):
    """1마디. 1~N개 코드 (시간 순). 한국 발라드/City Pop은 보통 1~3개."""
    chords: List[str] = Field(
        ..., min_length=1,
        description="이 마디 안 코드들 (왼쪽→오른쪽 시간순). 표기는 music21 호환.",
    )


class Part(BaseModel):
    """곡의 한 파트. 같은 곡에서 같은 이름의 파트는 하나의 정의를 공유한다.

    Real Book 스타일: 파트는 한 번만 정의하고 Song.structure에서 여러 번 참조.
    """
    name: str = Field(
        ...,
        description="파트 이름. Intro / Verse / Pre-Chorus / Chorus / Bridge / Outro 권장 (자유 입력 가능).",
    )
    bars: List[Bar] = Field(..., min_length=1)


class Song(BaseModel):
    """곡 전체 — 파트 정의 + 흐름.

    예: 파트 3개 정의(Intro/Verse/Chorus) + structure로 Verse 두 번, Chorus 두 번 흐름 표현.
    """
    parts: List[Part] = Field(..., min_length=1)
    structure: Optional[List[str]] = Field(
        default=None,
        description=(
            "파트 이름 시퀀스. 예: ['Intro','Verse','Chorus','Verse','Chorus','Bridge','Chorus','Outro']. "
            "생략하면 parts 순서대로 1번씩 재생되는 것으로 간주."
        ),
    )


class ArrangementInput(BaseModel):
    """편곡 요청 입력. 사용자 노출 옵션은 key / bpm / genre / free_text 4개."""
    song: Song
    key: str = Field(..., description="예: 'C major', 'A minor'")
    bpm: int = 100
    time_signature: str = "4/4"
    genre: GenreT
    free_text: Optional[str] = Field(
        default=None,
        description="자유 텍스트 묘사 (예: '밤 드라이브 느낌의 쓸쓸한 City Pop').",
    )


class ArrangementOutput(BaseModel):
    """편곡 결과. parts는 입력 song.parts와 같은 길이·이름·각 파트 마디 수를 유지."""
    parts: List[Part] = Field(
        ...,
        description="편곡된 파트 목록. 입력 song.parts와 1:1 대응 (이름·마디 수·각 마디 코드 수 동일).",
    )
    rationale: str = Field(..., description="어떤 변형을 했는지 1~3문장 한국어 설명")
    warnings: List[str] = Field(default_factory=list, description="적용 못 한 부분이나 충돌 사항")


# ----- 시스템 프롬프트 ---------------------------------------------------

# 동적인 부분(키별 함수표)은 _format_user_message에서 주입.
STRUCTURED_SYSTEM_PROMPT = """당신은 한국 발라드 / City Pop / Jazz 등 대중음악에 능숙한 편곡가입니다.
사용자의 곡(Song = parts + structure)과 키/장르/자유 묘사를 받아, 음악 이론을 지키면서
요청한 장르 색을 입힌 편곡을 JSON으로 응답합니다.

============================================================
입력 / 출력 구조 규칙 — 절대 위반 금지
============================================================
1. 출력의 parts는 입력 song.parts와 **이름·순서·길이**가 정확히 같아야 한다.
   - 파트 이름을 바꾸지 마라.
   - 파트를 추가/삭제하지 마라.
   - 각 파트의 마디 수를 그대로 유지하라.
2. 각 마디(Bar.chords)의 코드 개수도 **입력과 동일**하게 유지.
   - 1마디 3코드 입력 → 출력도 3코드. 한 마디를 두 마디로 쪼개거나 합치지 마라.
3. 코드 표기는 music21 파싱 가능한 일반 표기.
   좋은 예: C, Cm, Cmaj7, Cm7, C7, C9, Cm9, Cmaj9, Cdim, Caug, Csus4,
            C/E, F#m7b5, E7b9, E7#5, E7#9, A7alt
   피할 표기: Cmaj9#11sus4(다중 텐션 동시), C(add9b13), 한글 표기, 마디 번호
4. structure는 사용자가 정의한 곡 흐름이다 — 편곡이 변경하지 마라 (출력 스키마에는 포함하지 않으니
   parts만 반환하면 된다).

============================================================
음악 이론 — 절대 지킬 것
============================================================
A. 함수(function) 보존
   - 원본의 V7 → I/i 해결을 깨지 마라.
     예: E7 → Am 사이에 A9/A7을 끼우지 마라. A9는 D를 향하는 도미넌트라 흐름이 깨진다.
   - 원본의 ii-V-I이 보이면 보존하거나 더 풍부하게(ii7-V7-Imaj7, ii9-V13-Imaj9 등).
   - 알터드 도미넌트(E7#5, A7b9, G7#9, B7alt 등)는 의도된 텐션이다.
     절대 단순 7th로 단순화하지 마라. 오히려 텐션을 한 단계 더 강화해도 된다.
   - 슬래시 코드는 (a)전위 (b)베이스 페달 (c)passing 중 어느 기능인지 분명히 하라.
     예: C/D는 D 베이스 페달 위 D11/D9sus 사운드. 단순 'C'로 바꾸면 페달 효과가 사라진다.

B. Roman numeral 함수 분석
   메이저 키: I ii iii IV V vi vii°
   ii-V-I = (ii의 코드) → (V의 코드) → (I의 코드).
   슬래시 코드의 베이스가 같은 코드의 다른 음이면 전위(I⁶ 등)이고,
   베이스가 다른 음(특히 5도 위/아래)이면 페달이거나 진행 코드다.
   ※ 'I → I/B → V'는 ii-V-I이 아니라 단순 베이스 진행이다 — 헷갈리지 마라.

C. 보이스 리딩
   인접 마디 간 루트 모션은 완전 4/5도 또는 반음/온음 진행이 자연스럽다.
   장르 색을 위한 7/9/11/13 텐션은 인접 코드와 부드럽게 연결되도록.

============================================================
장르 색 가이드 (지나친 적용 금지)
============================================================
City Pop:   Imaj7/IVmaj7, ii9, V9/V13, slash chord 베이스 페달, ii-V-I 풍부
Jazz:       텐션 적극, tritone substitution(V7 → bII7), altered dominant(7#5 / 7b9 / 7alt)
Ballad:     다이어토닉 + 7th 위주, 차분하고 단순한 진행
Lo-fi:      maj7 / m7 위주, drowsy하고 단순, 변화 적음
Bossa Nova: maj7/m7/7 + slash, 부드러운 크로마틱 어프로치

============================================================
Few-shot
============================================================

[예시 1] G major / City Pop / 사랑하기 때문에 풍 발라드
입력 Verse 4마디:
  ["G", "CM7"], ["Bm7", "E7#5", "E7"], ["Am9", "C/D", "D7"], ["Gsus4", "G"]
좋은 편곡:
  ["GM7", "CM7"], ["Bm7", "E7#5", "E7b9"], ["Am9", "D11", "D9"], ["Gsus4", "GM7"]
근거: 알터드 E7#5 보존하고 E7→E7b9로 텐션 한 단계. C/D는 기능을 분명히 D11로.
       D7→D9로 City Pop 색. 마지막 G→GM7로 7th 정착.
나쁜 편곡 (절대 하지 말 것):
  ["G", "CM7"], ["Bm7", "E7", "A9"], ["Am7", "C", "D9"], ["Gsus4", "G"]
이유: A9 끼워서 E7→Am 해결 깨짐, E7#5 알터드 사라짐, C/D의 D 페달 사라짐.

[예시 2] C major / Jazz
입력 8마디:
  ["Dm7", "G7"], ["CM7"], ["Em7", "A7"], ["Dm7", "G7"]
좋은 편곡:
  ["Dm9", "G13"], ["CM9"], ["Em7", "A7b9"], ["Dm7", "Db7"]
근거: ii-V-I (Dm-G-C) 보존하면서 9/13 텐션. A7은 V/ii(Dm)이라 b9 알터드.
       마지막 G7을 Db7로 tritone substitute해 Jazz 색.

[예시 3] A minor / Ballad
입력 4마디:
  ["Am"], ["F", "G"], ["Em", "Am"], ["Dm", "E7"]
좋은 편곡:
  ["Am9"], ["FM7", "G"], ["Em7", "Am7"], ["Dm7", "E7b9"]
근거: 다이어토닉 + 7/9 텐션 적당히. E7은 V/i(Am)라 b9로 마이너 키 도미넌트 색 강화.
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


def _song_to_text(song: Song) -> str:
    """Song을 LLM이 읽기 쉬운 멀티라인 텍스트로 직렬화."""
    lines: List[str] = []
    lines.append("[Parts]")
    for part in song.parts:
        bars_str = " | ".join(" ".join(bar.chords) for bar in part.bars)
        lines.append(f"  {part.name} ({len(part.bars)} bars): {bars_str}")
    lines.append("")
    lines.append("[Structure]")
    if song.structure:
        lines.append("  " + " → ".join(song.structure))
    else:
        lines.append("  " + " → ".join(p.name for p in song.parts) + "  (parts 순서대로 1회씩)")
    return "\n".join(lines)


def _format_user_message(req: ArrangementInput) -> str:
    table = function_table_text(req.key)
    out = [
        "============================================================",
        "곡 정보",
        "============================================================",
        _song_to_text(req.song),
        "",
        f"Key: {req.key}",
        f"BPM: {req.bpm}",
        f"Time signature: {req.time_signature}",
        f"Genre: {req.genre}",
    ]
    if req.free_text:
        out.append(f"Free text: {req.free_text}")
    out += [
        "",
        "============================================================",
        "이 곡 키의 함수표 (이걸 기준으로 함수 분석할 것)",
        "============================================================",
        table,
        "",
        "============================================================",
        "지시",
        "============================================================",
        "위 곡의 각 파트를 편곡한 결과를 JSON으로 출력하세요.",
        "- 출력 parts는 입력 parts와 이름·순서·마디 수·각 마디 코드 수가 동일해야 합니다.",
        "- 시스템 프롬프트의 함수 보존 규칙(특히 V7→I/i 해결, 알터드 도미넌트 보존, "
        "슬래시 코드 기능)을 절대 어기지 마세요.",
        f"- {req.genre} 장르 색을 입히되 지나치지 않게 하세요.",
    ]
    if req.free_text:
        out.append("- free_text의 분위기를 반영하되 음악 이론 규칙이 우선입니다.")
    return "\n".join(out)


def _validate_shape(req_song: Song, out_parts: List[Part]) -> List[str]:
    """LLM 출력의 구조(파트 이름·길이·각 마디 코드 수)가 입력과 일치하는지 검사.

    문제가 있으면 사람이 읽을 수 있는 메시지 리스트 반환. 비어 있으면 OK.
    """
    issues: List[str] = []
    if len(out_parts) != len(req_song.parts):
        issues.append(
            f"parts 개수 불일치: 입력 {len(req_song.parts)} vs 출력 {len(out_parts)}"
        )
        return issues  # 길이 안 맞으면 이후 비교는 의미 없음

    for i, (in_p, out_p) in enumerate(zip(req_song.parts, out_parts)):
        if in_p.name != out_p.name:
            issues.append(
                f"parts[{i}] 이름 변경됨: {in_p.name!r} → {out_p.name!r}"
            )
        if len(in_p.bars) != len(out_p.bars):
            issues.append(
                f"parts[{i}]({in_p.name}) 마디 수 불일치: "
                f"{len(in_p.bars)} vs {len(out_p.bars)}"
            )
            continue
        for bi, (in_b, out_b) in enumerate(zip(in_p.bars, out_p.bars)):
            if len(in_b.chords) != len(out_b.chords):
                issues.append(
                    f"parts[{i}]({in_p.name}).bars[{bi}] 코드 개수 불일치: "
                    f"{len(in_b.chords)} vs {len(out_b.chords)}"
                )
    return issues


def arrange_structured(
    req: ArrangementInput,
    model: str = DEFAULT_MODEL,
) -> ArrangementOutput:
    """Song(파트+구조) 입력 → 파트별 편곡 출력.

    OpenAI structured output을 사용해 ArrangementOutput Pydantic 스키마로 강제 파싱한다.
    음악적 함수 보존(V7 해결, 알터드 보존 등)은 시스템 프롬프트와 키별 함수표로 안내하고,
    구조 일치(파트 이름·마디 수·각 마디 코드 수)는 응답 후 _validate_shape로 검증한다.
    검증 실패 시 호출자(API 라우트)가 재시도하거나 warnings로 노출한다.
    """
    if not req.song.parts:
        raise LLMArrangerError("song.parts가 비어 있습니다.")

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
