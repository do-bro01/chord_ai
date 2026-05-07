"""기능 3: OpenAI API 기반 편곡 요청

추출된 코드 진행과 사용자의 자연어 요청을 받아
편곡된 코드 진행을 텍스트로 반환한다.
"""

from __future__ import annotations

import os
import re
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = "gpt-4o"

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


class LLMArrangerError(RuntimeError):
    pass


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMArrangerError(
            "OPENAI_API_KEY 환경변수가 설정되지 않았습니다. "
            ".env 파일을 확인하세요."
        )
    return OpenAI(api_key=api_key)


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
