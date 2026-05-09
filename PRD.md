# PRD: chord_ai — AI 기반 코드 리하모니제이션 및 편곡 보조 툴

## 1. 프로젝트 개요

사용자가 **코드 진행을 직접 입력**(또는 음원에서 추출)하고, **구조화된 편곡 옵션 + 보조 자유 텍스트**를 바탕으로 LLM과 함께 코드를 재구성·텐션 추가·치환·연결 개선하며, **MIDI로 즉시 청음**한 뒤 만족하면 악보(MusicXML / MIDI / PDF)로 export 하는 로컬 실행 웹 애플리케이션.

> 이전 PRD(자동 코드 추출 + 자유 텍스트 LLM 편곡 중심)에서 방향 전환됨. 배경은 [issue.md](issue.md)의 항목 13 참고.

### 1-1. 핵심 방향

- **자동 작곡 AI가 아님** — 코드 기반 편곡 보조 툴.
- **MP3 자동 추출이 아니라 사용자 코드 입력이 1급 시민** — 추출 정확도의 본질적 한계를 회피.
- **자유 텍스트가 아니라 구조화 옵션이 핵심 제어** — LLM 결과의 비결정성을 줄임.
- **생성형 오디오가 아니라 MIDI 기반 미리듣기** — 비용·지연·품질 문제 회피.
- **LLM 단독이 아니라 규칙 기반 + LLM 혼합** — 표기·다이어토닉·music21 호환성을 룰로 검증.

### 1-2. 비목표 (Non-Goals)

- 자동 작곡 / 멜로디 생성
- 생성형 오디오 (Suno, MusicGen 등)
- MP3 추출의 100% 정확도 (한계는 인정·안내)
- 풀밴드 합주 MIDI (드럼·EP는 v2)
- 마디 단위 부분 편곡, 곡 형식 자동 분석 (v2)

---

## 2. MVP 범위

| 단계 | MVP 포함 | v2 이후 |
|---|---|---|
| 입력 | 코드 직접 입력, MP3 추출(보조), Key/BPM/박자 입력 또는 자동 추정 | 멜로디 입력, 가사, 곡 형식 자동 분석 |
| 편곡 옵션 | 장르/복잡도/텐션/베이스 스타일/리듬 (구조화) + 자유 텍스트 보조 | 마디별 옵션, 섹션별 옵션 차등 |
| LLM 편곡 | 리하모니제이션, 텐션 추가, 치환, 연결 개선 + 룰 베이스 검증 | 멜로디 동시 편곡, 보이싱 자동 결정 |
| 청음 | MIDI 기반 즉시 재생 (피아노 + 베이스 2트랙) | 드럼, EP, 워킹 베이스, 보이싱 다양화 |
| 대화 수정 | structured state 유지 + diff 적용 | 마디 단위 부분 수정, 변경 이력 시각화 |
| Export | MusicXML, MIDI, PDF | 코드 차트 PNG, 가이드 톤 표시 |

---

## 3. 핵심 기능 (단계별)

### 단계 1. 입력

#### A. 코드 직접 입력 (메인)

- 텍스트 입력 또는 마디별 칩 단위 입력.
- 코드 표기: `C`, `Am`, `Cmaj7`, `D7`, `F#m7b5`, `C/E` 등 일반 표기 지원.
- 함께 받는 메타데이터:
  - **Key** — 예: `C major`, `A minor`. 모르면 "자동 추정" 버튼 (qm-keydetector 재사용 가능).
  - **BPM** — 기본 100, 사용자 조정 가능.
  - **박자(Time signature)** — 기본 4/4.
  - **마디 수** — 입력 코드 수에서 자동 산출 (또는 명시).

#### B. MP3 추출 (보조)

- 기존 추출 파이프라인 재사용:
  [audio_analysis.py](audio_analysis.py),
  [chordino_extractor.py](chordino_extractor.py),
  [bass_detector.py](bass_detector.py),
  [chord_postprocess.py](chord_postprocess.py).
- **명시적 안내** 필수 (issue.md 9·10번 결과 반영):
  - "추출된 코드는 부정확할 수 있으며 수정이 필요할 수 있습니다."
  - "sus 코드, 9th/11th 같은 텐션은 감지되지 않습니다."
  - "CM7 ↔ Em7, Bm7 ↔ D 같은 상부구조 모호성이 남을 수 있습니다."
- 추출 후 사용자가 직접 수정 가능한 편집 UI(직접 입력 UI 재사용).

---

### 단계 2. 편곡 옵션 입력

#### 구조화 옵션 (핵심 제어)

| 옵션 | 값 |
|---|---|
| 장르 | City Pop / Jazz / Ballad / Lo-fi / Bossa Nova |
| 코드 복잡도 | 단순 / 보통 / 복잡 |
| 텐션 사용량 | 적음 / 보통 / 많음 |
| 베이스 스타일 | 루트 중심 / 부드러운 연결 / 워킹 베이스 |
| 리듬 성향 | 안정적 / 싱코페이션 / 펑키함 |

#### 자유 텍스트 (보조 입력)

- 분위기 묘사: "밤 드라이브 느낌", "잔잔하지만 세련된 느낌".
- 감성 보완용. **핵심 제어는 구조화 옵션이 담당**, 자유 텍스트는 보조.

#### 옵션 충돌 처리

- 충돌 가능한 조합(예: Lo-fi + 워킹 베이스 + 펑키함)은 룰 베이스로 사전 경고.

---

### 단계 3. AI 편곡 엔진

#### LLM 역할 (제한된 범위)

- **스타일 해석** — 구조화 옵션 + 자유 텍스트 → 편곡 의도.
- **코드 변형 제안**:
  - **Reharmonization**: 같은 진행을 다른 코드로 재구성 (예: `C-Am-F-G` → `Em7-A7-Dm7-G7`, II-V-I로 재해석).
  - **Tension 추가**: 트라이어드에 7/9/11/13 추가 (예: `C` → `Cmaj9`).
  - **Substitute chord**: 트라이톤 대리, relative minor 등 (예: `G7` → `Db7`).
  - **연결 개선 (voice leading)**: passing chord, slash chord (예: `C-G-Am` → `C-G/B-Am`).

#### LLM 입력 스키마 (structured)

```json
{
  "current_chords": ["C", "Am", "F", "G"],
  "key": "C major",
  "bpm": 100,
  "time_signature": "4/4",
  "section_size_bars": 8,
  "options": {
    "genre": "Jazz",
    "complexity": "보통",
    "tension": "많음",
    "bass_style": "워킹 베이스",
    "rhythm": "싱코페이션"
  },
  "free_text": "밤 드라이브 느낌"
}
```

#### LLM 출력 스키마 (structured JSON)

```json
{
  "chords": ["Cmaj9", "Am7", "Dm7", "G13"],
  "rationale": "II-V-I 진행으로 재해석, 텐션 9/13 추가",
  "warnings": []
}
```

> 자유 텍스트 응답을 정규식으로 파싱하지 않음 — OpenAI structured output(JSON Schema) 또는 tool-calling으로 강제.

#### 룰 베이스 검증 레이어 (LLM 출력 후처리)

LLM은 잘못된 표기·키 이탈·music21 미지원 표기를 자주 만든다. 이를 검증하지 않으면 export 단계에서 silent fail로 이어진다 (issue.md 11번).

1. **표기 정규화** — [chord_postprocess.py](chord_postprocess.py)의 `normalize_label()` 재사용.
2. **키 다이어토닉 체크** — 키 안에 있는 코드인가? 비다이어토닉이면 borrowed/secondary dominant로 정당한가?
3. **부적격 코드는** 가까운 다이어토닉으로 스냅하거나 LLM에 재요청.
4. **music21 파싱 사전 검증** — `harmony.ChordSymbol` 어휘로 먼저 파싱 시도.

#### 규칙 기반 + LLM 혼합 — 분담

| 작업 | 담당 |
|---|---|
| 스타일 해석, 코드 변형 제안 | LLM |
| 표기 정규화, 다이어토닉 검증 | 룰 |
| 베이스 라인 생성, MIDI 렌더링 | 룰 (DSP) |
| 악보 생성 | 룰 (music21) |

#### 편곡 단위

- 곡 전체를 한 번에 편곡하지 않고 **8마디 또는 verse/chorus 섹션 단위**로 분할.
- 이유:
  1. 토큰 비용 절감.
  2. 섹션 간 일관성을 LLM에 떠넘기지 않음.
  3. 부분 수정 용이.
  4. 캐싱 가능.

---

### 단계 4. MIDI 미리듣기

#### MVP 범위 — 2트랙

- **피아노** — 코드를 그대로 보이싱해서 깔기.
- **베이스** — 매 마디 첫 박에 루트만 (가장 단순).

#### v2 확장

- **베이스**: 워킹/연결형 패턴 알고리즘.
- **드럼**: 장르별 패턴 라이브러리 (8비트 / 보사노바 / 스윙 / 펑크).
- **EP**: stab + sustain 보이싱 패턴.

#### 구현

- 기존 [audio_renderer.py](audio_renderer.py)
  (pretty_midi + fluidsynth + FluidR3_GM.sf2) 재사용·확장.
- 프론트는 사전 렌더링한 짧은 WAV를 즉시 재생 (브라우저 호환성·구현 단순함).
- 편곡 결과 변경 시 자동 재렌더링, 동일 입력은 캐시.

---

### 단계 5. 대화 기반 수정

#### 상태 관리 — structured JSON (chat history 누적 X)

- 현재 편곡 상태를 클라이언트(또는 세션 DB)에 JSON으로 보관:

```json
{
  "session_id": "...",
  "current_chords": ["Cmaj9", "Am7", "Dm7", "G13"],
  "key": "C major", "bpm": 100, "time_signature": "4/4",
  "options": { "genre": "Jazz", "complexity": "보통", ... },
  "history": [
    { "turn": 1, "user_input": "재즈로 바꿔줘", "diff": [...] },
    { "turn": 2, "user_input": "베이스 줄여줘", "diff": [...] }
  ]
}
```

- LLM 호출 시 **전체 chat history가 아니라 현재 상태 + 사용자 수정 요청만** 전달.
- 이유: 토큰 효율, 결정성, 디버깅 용이성.

#### 예시 사용자 수정 요청

| 사용자 발화 | 시스템 처리 |
|---|---|
| "좀 더 재즈스럽게" | LLM이 옵션 자동 조정 제안 (예: tension=많음, complexity=복잡) → 코드 재생성 |
| "베이스 움직임 줄여줘" | bass_style을 "루트 중심"으로 변경 후 재편곡 |
| "코드 너무 복잡해" | complexity 한 단계 낮춤 |

---

### 단계 6. 최종 출력 (Export)

- **MusicXML** — `music21.stream.Stream.write('musicxml')`.
- **MIDI** — pretty_midi 또는 music21.
- **PDF** — MuseScore CLI로 MusicXML 렌더링 (기존 [score_generator.py](score_generator.py) 재사용).
- 출력 경로: `output/`.

---

## 4. 시스템 구조

### 4-1. 디렉토리 (변경 후)

```
chord_ai/
├── PRD.md                       # 본 문서
├── design.md
├── issue.md
├── tbc.md
│
├── audio_analysis.py            # MP3 추출 (보조 진입점으로 유지)
├── chordino_extractor.py
├── bass_detector.py
├── chord_postprocess.py         # ★ LLM 출력 검증에도 재사용
├── bar_grouper.py
├── llm_arranger.py              # ★ 구조화 입력/출력으로 재작성
├── score_generator.py
├── audio_renderer.py            # ★ MIDI preview + 최종 WAV 양쪽 지원
├── main.py                      # CLI 진입점 (기존 흐름 유지)
│
├── backend/
│   ├── api/
│   │   ├── audio.py             # POST /api/audio/extract (기존)
│   │   ├── arrange.py           # ★ POST /api/arrange (신규)
│   │   ├── preview.py           # ★ POST /api/preview (MIDI/WAV 렌더)
│   │   └── export.py            # ★ POST /api/export (MusicXML/MIDI/PDF)
│   ├── auth/                    # 기존
│   └── db/                      # 기존
│
└── frontend/
    ├── app/
    │   ├── page.tsx                    # ★ 코드 입력 메인 화면으로 변경
    │   ├── (auth)/...                  # 기존
    │   └── arrange/page.tsx            # ★ 편곡 워크스페이스
    └── components/
        ├── chord/
        │   ├── ChordInput.tsx          # ★ 직접 입력 UI
        │   ├── ChordChart.tsx          # ★ 마디별 칩
        │   └── KeyBpmMeter.tsx         # ★ Key/BPM/박자 입력
        ├── extract/
        │   └── Mp3Extractor.tsx        # ★ MP3 보조 진입점 (정확도 경고)
        ├── arrange/
        │   ├── OptionPanel.tsx         # ★ 5개 구조화 옵션
        │   ├── FreeTextHint.tsx        # ★ 자유 텍스트 보조
        │   ├── PreviewPlayer.tsx       # ★ MIDI 즉시 재생
        │   └── RefineChat.tsx          # ★ 대화형 수정
        └── export/
            └── ExportPanel.tsx         # ★ MusicXML/MIDI/PDF 다운로드
```

### 4-2. 데이터 흐름

```
[1. 입력]
  코드 직접 입력 ──┐
                   ├─→ { chords, key, bpm, time_sig }
  MP3 추출 ────────┘   (+ 추출 시 정확도 경고)
        │
        ▼
[2. 편곡 옵션]  OptionPanel + FreeTextHint
        │
        ▼
[3. AI 편곡]  POST /api/arrange
   ├─→ LLM (structured input → structured output)
   └─→ 룰 검증 (normalize + 다이어토닉 + music21 파싱 체크)
        │
        ▼
[4. MIDI Preview]  POST /api/preview → MIDI/WAV
   PreviewPlayer 즉시 재생
        │
        ▼
[5. 대화 수정]  RefineChat
   현재 state + diff request → 재편곡 → 재미리듣기
        │
        ▼
[6. Export]  POST /api/export → MusicXML / MIDI / PDF
```

---

## 5. 기술 스택 (변경 사항만)

**유지**
- Python 3.12, FastAPI, SQLAlchemy, music21, pretty_midi, fluidsynth, OpenAI API, Next.js (App Router).
- demucs, autochord, chordino, vamp, NNLS-Chroma → MP3 추출 보조 진입점에 그대로 사용.

**추가 검토**
- LLM structured output: OpenAI JSON Schema(또는 tool calling)로 응답 형식 강제.
- 프론트 MIDI 재생: MVP는 사전 렌더 WAV로 단순화. v2에서 `Tone.js` 등 검토.
- 코드 입력 UX: 의존성 최소화를 위해 라이브러리 없이 자체 구현.

---

## 6. 환경/제약

- 로컬 macOS (Apple M3 Pro) 단일 사용자 환경.
- LLM: `gpt-4o` 또는 신규 모델 (structured output 지원 필수).
- 파일 업로드 50MB 제한 (기존 유지).
- 모든 산출물은 `output/`에 저장.
- 환경변수: 기존과 동일 (`OPENAI_API_KEY`, JWT/SMTP/Google OAuth 등은 [design.md](design.md) 참고).

---

## 7. 완료 기준 (MVP)

- [ ] 사용자가 코드 진행을 직접 입력하면 마디 단위 칩으로 표시됨.
- [ ] MP3를 업로드하면 코드가 추출되고, **정확도 한계 안내가 명확히 표시됨**.
- [ ] Key/BPM/박자를 입력 또는 자동 추정으로 결정 가능.
- [ ] 5개 구조화 옵션 + 자유 텍스트로 편곡 요청 가능.
- [ ] LLM 편곡 결과가 **룰 검증을 통과해서** 화면에 표시됨.
- [ ] 편곡 결과를 MIDI로 즉시 청음 가능 (피아노 + 베이스 2트랙).
- [ ] 채팅으로 "좀 더 재즈스럽게" 같은 수정 요청 시 state가 누적되어 반영됨.
- [ ] MusicXML / MIDI / PDF 다운로드 가능.

---

## 부록 A. 이전 PRD 대비 변경점

| 영역 | 이전 | 신규 |
|---|---|---|
| 메인 입력 | MP3 업로드 | 코드 직접 입력 |
| MP3 추출 | 1급 기능 | 보조 진입점 (한계 안내 포함) |
| LLM 입력 | 자유 텍스트만 | 구조화 옵션 + 자유 텍스트 |
| LLM 출력 | 자유 텍스트 → 정규식 파싱 | structured JSON + 룰 검증 |
| 편곡 단위 | 곡 전체 한 번 | 8마디 / 섹션 단위 |
| 청음 | 최종 WAV만 | MIDI 즉시 미리듣기 + 최종 export |
| 대화 수정 | 단발성 요청 | structured state 누적 |
| Export | PDF + WAV | MusicXML + MIDI + PDF |
| MIDI 트랙 | 1트랙 (코드만) | 2트랙 (피아노 + 베이스, MVP) |
