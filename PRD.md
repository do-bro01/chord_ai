# PRD: Music AI — 음원 분석 및 편곡 시스템

## 프로젝트 개요

음원 파일을 업로드하면 코드 진행을 추출하고, Anthropic LLM을 활용해 사용자의 자연어 요청에 따라 편곡한 뒤 악보와 오디오 파일로 출력해주는 로컬 실행 파이썬 프로그램.

---

## 환경 정보

| 항목 | 내용 |
|---|---|
| 프로젝트 경로 | `/Users/do_bro/GitHub/chord_ai` |
| 가상환경 | `/Users/do_bro/GitHub/chord_ai/venv` |
| 가상환경 활성화 | `source venv/bin/activate` |
| SoundFont 경로 | `/Users/do_bro/GitHub/chord_ai/soundfonts/FluidR3_GM.sf2` |
| 실행 환경 | 로컬 macOS (Apple M3 Pro, 18GB) |

---

## 설치된 도구 및 라이브러리

**Python 라이브러리**
- `librosa` — 오디오 로드, 코드 추출
- `music21` — 악보 생성, MIDI 변환
- `pretty_midi` — MIDI 조작
- `pyfluidsynth` — fluidsynth Python 제어
- `numpy`, `scipy` — 수치 연산
- `anthropic` — LLM 편곡 요청

**시스템 도구**
- `fluidsynth` — MIDI → WAV 렌더링 (brew 설치)
- `MuseScore` — 악보 렌더링 및 PDF 출력 (brew cask 설치)

---

## 목표 기능 (구현 순서)

### 기능 1. 음원 파일 로드
- 지원 포맷: `.mp3`, `.wav`, `.flac`, `.m4a`, `.ogg`
- `librosa.load()`로 로드, 16kHz 모노로 리샘플링
- 로드 실패 시 명확한 에러 메시지 출력

### 기능 2. 코드 진행 추출
- `librosa`의 크로마 특징(chroma feature) 기반으로 각 마디별 코드 추출
- 출력 형식 예시: `Am - F - C - G`
- 추출된 코드 진행을 사용자에게 텍스트로 출력

### 기능 3. LLM 편곡 요청 (Anthropic API)
- 추출된 코드 진행을 컨텍스트로 Anthropic API에 전달
- 사용자의 자연어 요청을 함께 전달 (예: "슬프게 편곡해줘", "기타 솔로 느낌으로")
- LLM이 편곡된 코드 진행을 텍스트로 반환
- 대화 흐름:
  1. 코드 추출 결과 출력
  2. LLM이 "편곡하시겠습니까?" 질문
  3. 사용자가 원하는 느낌 입력
  4. LLM이 편곡된 코드 진행 반환

### 기능 4. 악보 생성
- `music21`으로 편곡된 코드 진행을 악보로 변환
- MuseScore로 렌더링하여 PDF 또는 PNG로 출력
- 출력 파일 저장 경로: `/Users/do_bro/GitHub/chord_ai/output/`

### 기능 5. 오디오 파일 생성
- `pretty_midi`로 편곡된 코드 진행을 MIDI로 변환
- `pyfluidsynth` + FluidR3_GM.sf2 SoundFont로 MIDI → WAV 렌더링
- 코드를 하나씩 순서대로 들을 수 있도록 각 코드 사이에 간격 부여
- 출력 파일 저장 경로: `/Users/do_bro/GitHub/chord_ai/output/`

---

## 디렉토리 구조

```
chord_ai/
├── venv/
├── soundfonts/
│   └── FluidR3_GM.sf2
├── output/                  # 생성된 악보, 오디오 저장
├── uploads/                 # 업로드된 음원 파일 저장
├── main.py                  # 메인 실행 파일
├── audio_analysis.py        # 기능 1, 2: 오디오 로드 + 코드 추출
├── llm_arranger.py          # 기능 3: Anthropic API 편곡 요청
├── score_generator.py       # 기능 4: 악보 생성
├── audio_renderer.py        # 기능 5: 오디오 파일 생성
├── .env                     # ANTHROPIC_API_KEY 저장
└── requirements.txt
```

---

## 실행 흐름

```
python main.py 음원파일.mp3
       ↓
[오디오 로드] librosa로 로드 및 전처리
       ↓
[코드 추출] 크로마 특징 기반 코드 진행 추출
       ↓
출력: "추출된 코드 진행: Am - F - C - G"
       ↓
[LLM 대화] "편곡하시겠습니까?"
       ↓
사용자 입력: "슬픈 느낌의 기타 솔로로 편곡해줘"
       ↓
[Anthropic API] 편곡된 코드 진행 반환
       ↓
출력: "편곡된 코드 진행: Am - Em - Dm - E"
       ↓
[악보 생성] music21 + MuseScore → PDF/PNG
       ↓
[오디오 생성] pretty_midi + fluidsynth → WAV
       ↓
output/ 폴더에 결과 저장
```

---

## 환경변수

`.env` 파일에 아래 내용 저장:
```
ANTHROPIC_API_KEY=your_api_key_here
```

---

## 제약 조건

- 모든 기능은 **로컬에서만 실행** (서버 배포 없음, 이 단계에서는)
- UI 없음 — **CLI(터미널) 기반**으로 먼저 구현
- LLM은 **Anthropic API** 사용 (`claude-sonnet-4-20250514` 모델 권장)
- 출력 파일은 항상 `output/` 폴더에 저장

---

## 완료 기준

- [ ] `.mp3` 파일을 CLI로 입력하면 코드 진행이 텍스트로 출력됨
- [ ] LLM과 대화를 통해 편곡 스타일 요청이 가능함
- [ ] 편곡된 코드 진행이 텍스트로 출력됨
- [ ] `output/` 폴더에 악보 파일(PDF or PNG)이 생성됨
- [ ] `output/` 폴더에 WAV 오디오 파일이 생성됨
