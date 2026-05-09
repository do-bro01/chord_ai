# To Be Continued — chord_ai 프로젝트 핸드오프

> 이 파일은 새 Claude Code 세션에서 작업을 이어가기 위한 컨텍스트 정리입니다.
> 마지막 업데이트: 2026-05-09 (프로젝트 방향 전환 반영)

---

## 1. 프로젝트 한 줄 요약

**chord_ai** — **AI 기반 코드 리하모니제이션 및 편곡 보조 툴**.
사용자가 코드 진행을 직접 입력(또는 MP3에서 추출)하고, 구조화된 편곡 옵션 + 자유 텍스트 보조로 LLM과 함께 코드를 재구성·텐션 추가·치환하며, MIDI로 즉시 청음한 뒤 만족하면 MusicXML/MIDI/PDF로 export 하는 로컬 실행 웹 앱.

> **2026-05-09 방향 전환**: 이전에는 "MP3 자동 추출 + 자유 텍스트 LLM 편곡"이 메인이었으나, 추출 정확도 한계(이슈 2/8/9/10) + 자유 텍스트 LLM의 비결정성 때문에 **"코드 직접 입력 + 구조화 옵션 LLM"** 방향으로 전환. 자세한 배경은 [issue.md](issue.md) 항목 13.

전체 스펙은 [PRD.md](PRD.md) 참고.

---

## 2. 환경

| 항목      | 값                                                        |
| --------- | --------------------------------------------------------- |
| 경로      | `/Users/do_bro/GitHub/chord_ai`                           |
| Python    | 3.12 (autochord/TF wheel 호환 위해 3.14에서 다운그레이드) |
| 가상환경  | `venv/` (활성화: `source venv/bin/activate`)              |
| 백업 venv | `venv-py314-backup/` (사용 안 함, 보관용)                 |
| ML 가속   | PyTorch MPS (Apple M3 Pro)                                |
| SoundFont | `soundfonts/FluidR3_GM.sf2`                               |
| OpenAI 키 | `.env`에 `OPENAI_API_KEY` 설정됨                          |

---

## 3. 디렉토리 구조 (현재)

```
chord_ai/
├── PRD.md                    # 제품 요구사항 (★ 2026-05-09 전면 개편)
├── design.md                 # 디자인/UI 흐름 (★ 신규 흐름 반영)
├── issue.md                  # 개발 중 이슈 13건 (★ #13 = 방향 전환 기록)
├── memo.md                   # 잡메모
├── tbc.md                    # ← 이 파일
├── main.py                   # CLI 진입점 (기존, MP3 → 편곡 흐름)
├── audio_analysis.py         # demucs + autochord/chordino 파이프라인
├── chordino_extractor.py     # NNLS-Chroma + chordino
├── bass_detector.py          # 베이스 stem 기반 코드 정정
├── chord_postprocess.py      # 표기 정규화 + 다이어토닉 보정 (★ LLM 출력 검증에도 재사용 예정)
├── bar_grouper.py            # 마디 단위 묶음
├── llm_arranger.py           # OpenAI 편곡 (★ structured I/O로 재작성 필요)
├── score_generator.py        # music21 악보 생성
├── audio_renderer.py         # MIDI → WAV (★ MVP에서 피아노+베이스 2트랙으로 확장)
├── requirements.txt
├── chord_ai.db               # SQLite DB (인증/세션)
├── 유재하-사랑하기 때문에-Acoustic Guitar.mp3   # 테스트용 음원
├── soundfonts/FluidR3_GM.sf2
├── output/                   # 생성 결과물
├── uploads/                  # 업로드 임시 저장소
├── venv/                     # Python 3.12
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── api/audio.py          # POST /api/audio/extract (기존)
│   ├── auth/                 # 인증/세션
│   └── db/
└── frontend/
    ├── app/page.tsx          # 현재는 업로드 중심 (★ 코드 입력 메인으로 재설계 필요)
    ├── components/Uploader.tsx
    └── ...
```

---

## 4. 지금까지 진행된 작업 (마일스톤)

- 백엔드 1차 개발 (FastAPI + 인증 + audio extract API)
- 프론트엔드 1차 개발 (Next.js, 업로드 중심 UI)
- 코드 추출 알고리즘 진화: librosa 크로마 템플릿 → demucs + autochord → **demucs + chordino + bass 정정 + 다이어토닉 보정 + 표기 정규화** (현재)
- 정확도 평가/한계 식별 (이슈 8~10)
- **2026-05-09 — 프로젝트 방향 전환 결정 + 문서 갱신**
  - PRD.md 전면 개편
  - design.md UI 흐름 갱신
  - issue.md 항목 13 추가

---

## 5. 신규 방향 — MVP 범위 요약

| 단계 | MVP에서 만들 것 |
|---|---|
| 1. 입력 | 코드 직접 입력 + (보조) MP3 추출 + Key/BPM/박자 |
| 2. 옵션 | 장르 / 복잡도 / 텐션 / 베이스 스타일 / 리듬 (구조화) + 자유 텍스트 보조 |
| 3. 편곡 | LLM(structured JSON) + 룰 검증 (normalize + 다이어토닉 + music21 파싱 체크) |
| 4. 청음 | MIDI 즉시 재생 (피아노 + 베이스 2트랙) |
| 5. 수정 | structured state 누적, 사용자 발화 → diff |
| 6. Export | MusicXML / MIDI / PDF |

상세는 [PRD.md](PRD.md) 참고.

---

## 6. 직전 상태

- **git 작업 트리**: 문서만 수정됨 (PRD.md / design.md / issue.md / tbc.md). 코드 변경 없음.
- **memo.md**: 거의 비어있음.
- **output/**: 비어있음.
- **신규 방향에 맞춘 코드 변경은 아직 시작 전**.

---

## 7. 다음 후보 작업 (신규 방향 구현)

### Phase 1 — 백엔드 골격
1. **`backend/api/arrange.py` 신규** — `POST /api/arrange` (structured input/output, 룰 검증 포함).
2. **`llm_arranger.py` 재작성** — OpenAI structured output(JSON Schema) 사용, 자유 텍스트 파싱 제거.
3. **`chord_postprocess.py` 확장** — LLM 출력 검증용 함수(다이어토닉 체크 + music21 파싱 사전 검증) 추가.
4. **`backend/api/preview.py` 신규** — `POST /api/preview` (코드 진행 + 옵션 → MIDI/WAV 렌더).
5. **`audio_renderer.py` 확장** — 피아노 + 베이스 2트랙 렌더링.
6. **`backend/api/export.py` 신규** — `POST /api/export` (MusicXML/MIDI/PDF).

### Phase 2 — 프론트엔드 재설계
7. **`/` 메인 화면 교체** — 업로더 → 코드 직접 입력 카드 (보조로 MP3 카드).
8. **`/arrange` 워크스페이스 신규** — OptionPanel + FreeTextHint + PreviewPlayer + RefineChat.
9. **MP3 추출 진입점 보존** — Mp3Extractor 컴포넌트 + 정확도 한계 경고 카피.
10. **상태 관리** — `arrangeState.ts` (현재 코드/옵션/history JSON 보관).

### Phase 3 — 통합
11. End-to-end 시나리오 검증: 직접 입력 흐름, MP3 보조 흐름.
12. 옵션 충돌 룰(예: Lo-fi + 워킹 베이스 + 펑키함) 경고 구현.
13. 캐시 정책(편곡 결과·MIDI 렌더 모두).

---

## 8. 새 세션에서 컨텍스트 빠르게 잡는 법

1. **이 파일 (`tbc.md`)** — 전체 핸드오프
2. **[PRD.md](PRD.md)** — 신규 방향 전체 스펙 (★ 우선)
3. **[issue.md](issue.md)** — 이미 해결된 13개 이슈 (특히 #13 = 방향 전환 배경)
4. **[design.md](design.md)** — UI 흐름·디자인 시스템
5. **기존 핵심 모듈**:
   - [audio_analysis.py](audio_analysis.py) — 추출 파이프라인 (재사용)
   - [chord_postprocess.py](chord_postprocess.py) — 정규화/다이어토닉 (LLM 검증에 재사용)
   - [llm_arranger.py](llm_arranger.py) — 재작성 대상
   - [audio_renderer.py](audio_renderer.py) — 2트랙 확장 대상
6. 필요 시 [backend/](backend/), [frontend/](frontend/)

---

## 9. 주의사항 (다시 밟으면 안 되는 함정)

- **`TF_USE_LEGACY_KERAS=1`은 autochord/TF import 이전에 설정해야 함** — [audio_analysis.py:21](audio_analysis.py#L21)에 `os.environ.setdefault`로 박혀있음. 이 줄을 import 아래로 옮기지 말 것.
- **venv는 Python 3.12** — `venv-py314-backup`은 사용 금지 (TF 미지원).
- **vamp 재설치 시** — `pip install --no-build-isolation vamp` (PEP 517 격리에서 numpy 못 찾음).
- **NNLS-Chroma 플러그인** — `~/Library/Audio/Plug-Ins/Vamp/`에 universal binary `.dylib`이 깔려 있어야 함. 의심되면 `file <path>`로 아키텍처 확인.
- **FastAPI 라우트에서 쿠키 헤더 다룰 때** — `Response`를 직접 만들어 거기에 쿠키 설정 후 반환. 의존성 주입된 `response`는 Pydantic 반환 시에만 유효 (이슈 1).
- **신규 LLM 출력은 자유 텍스트 파싱 금지** — structured JSON(OpenAI JSON Schema 또는 tool calling)으로 강제. 자유 텍스트 파싱은 이전 PRD의 fragility 원천 (이슈 13).
- **MP3 추출 결과를 메인으로 노출하지 말 것** — 보조 진입점 + 정확도 한계 경고 필수.
