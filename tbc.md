# To Be Continued — chord_ai 프로젝트 핸드오프

> 이 파일은 새 Claude Code 세션(다른 계정 로그인)에서 작업을 이어가기 위한 컨텍스트 정리입니다.
> 작성일: 2026-05-08

---

## 1. 프로젝트 한 줄 요약

**Music AI / chord_ai** — 음원 파일을 업로드하면 코드 진행을 추출하고, OpenAI LLM으로 편곡한 뒤 악보(PDF/PNG)와 오디오(WAV)를 출력하는 로컬 파이썬 프로그램. CLI + FastAPI 백엔드 + Next.js 프론트엔드 구조.

전체 스펙은 [PRD.md](PRD.md) 참고.

---

## 2. 환경

| 항목 | 값 |
|---|---|
| 경로 | `/Users/do_bro/GitHub/chord_ai` |
| Python | 3.12 (autochord/TF wheel 호환 위해 3.14에서 다운그레이드) |
| 가상환경 | `venv/` (활성화: `source venv/bin/activate`) |
| 백업 venv | `venv-py314-backup/` (사용 안 함, 보관용) |
| ML 가속 | PyTorch MPS (Apple M3 Pro) |
| SoundFont | `soundfonts/FluidR3_GM.sf2` |
| OpenAI 키 | `.env`에 `OPENAI_API_KEY` 설정됨 |

---

## 3. 디렉토리 구조 (현재)

```
chord_ai/
├── PRD.md                    # 제품 요구사항
├── design.md                 # 디자인 문서
├── issue.md                  # 개발 중 만난 이슈 7건 정리 (학습 노트)
├── memo.md                   # 잡메모
├── tbc.md                    # ← 이 파일
├── main.py                   # CLI 진입점
├── audio_analysis.py         # demucs + autochord 파이프라인
├── llm_arranger.py           # OpenAI 편곡
├── score_generator.py        # music21 악보 생성
├── audio_renderer.py         # MIDI → WAV
├── requirements.txt
├── chord_ai.db               # SQLite DB (백엔드 인증/세션용)
├── 유재하-사랑하기 때문에-Acoustic Guitar.mp3   # 테스트용 음원
├── soundfonts/FluidR3_GM.sf2
├── output/                   # 생성 결과물 (현재 비어있음)
├── uploads/                  # 업로드 파일 임시 저장소
├── venv/                     # Python 3.12
├── backend/                  # FastAPI
│   ├── main.py
│   ├── config.py
│   ├── api/                  # audio.py 등
│   ├── auth/                 # 인증/세션
│   └── db/
└── frontend/                 # Next.js
    ├── app/
    ├── components/
    ├── lib/
    ├── proxy.ts
    └── package.json
```

---

## 4. 지금까지 진행된 작업 (커밋 히스토리)

```
503b823 Update .gitignore                              ← HEAD (작업 트리 clean)
b8b0c4f .
e5b6c84 librosa 크로마 템플릿 방식 -> demucs + autochord
0c4e4f8 prd.md 수정
98748d0 음원 업로드
6aa9346 버그 수정
6b2d651 Update .gitignore
85bbaf2 Update .gitignore
fbe93c5 프론트 작업
4015659 백엔드 1차 개발
6b62cdc 문서 작성
b93d70a create repo
c35cbf9 Initial commit
```

핵심 마일스톤:
- 백엔드 1차 개발 (FastAPI + 인증)
- 프론트엔드 1차 개발 (Next.js)
- 코드 추출 알고리즘 전환: **librosa 크로마 템플릿 → demucs + autochord** (정확도 문제로 전환)
- 테스트 음원 업로드 (유재하 - 사랑하기 때문에 Acoustic Guitar)

---

## 5. PRD 5대 기능 진행 상황

| # | 기능 | 상태 | 파일 |
|---|---|---|---|
| 1 | 음원 파일 로드 | ✅ 구현 완료 | [audio_analysis.py](audio_analysis.py) |
| 2 | 코드 진행 추출 (demucs + autochord) | ✅ 구현 완료 | [audio_analysis.py](audio_analysis.py) |
| 3 | LLM 편곡 (OpenAI gpt-4o) | ✅ 구현 완료 | [llm_arranger.py](llm_arranger.py) |
| 4 | 악보 생성 (music21 + MuseScore) | ✅ 구현 완료 | [score_generator.py](score_generator.py) |
| 5 | 오디오 생성 (pretty_midi + fluidsynth) | ✅ 구현 완료 | [audio_renderer.py](audio_renderer.py) |
| + | FastAPI 백엔드 (인증/업로드/추출 API) | ✅ 구현 완료 | [backend/](backend/) |
| + | Next.js 프론트엔드 | ✅ 구현 완료 | [frontend/](frontend/) |

PRD의 완료 기준 5개 항목은 모두 구현된 상태(현재 코드 기준). 단, 실제 end-to-end 동작 검증/품질 평가는 사용자 판단이 필요.

---

## 6. 해결된 주요 이슈 (학습 노트)

[issue.md](issue.md)에 7건이 시간순으로 정리되어 있음. 요약:

1. **로그아웃 버튼 동작 안 함** — FastAPI에서 `Response`를 직접 반환하면 의존성 주입된 `response`의 헤더가 유실됨. Response 객체를 먼저 만들고 거기에 쿠키 삭제 후 반환하는 패턴으로 해결.
2. **코드 추출 정확도 부족** — librosa 24개 템플릿(maj/min)으로는 7th, sus 등 표현 불가 + 보컬·드럼 노이즈. → **demucs(stem 분리) + autochord(BTC 모델)** 조합으로 전환.
3. **Python 3.14에서 TF 설치 불가** — TF wheel 미지원. venv를 3.12로 재생성.
4. **vamp 패키지 빌드 실패** — PEP 517 build isolation에서 numpy 못 찾음. `pip install --no-build-isolation vamp`로 해결.
5. **autochord 모델 로딩 실패 (Keras 3 호환성)** — TF 2.16+ 기본 Keras 3가 레거시 SavedModel 못 읽음. `tf-keras` 설치 + `TF_USE_LEGACY_KERAS=1` 환경변수로 해결. **import 이전에** 환경변수 설정 필수 ([audio_analysis.py:21](audio_analysis.py#L21)).
6. **NNLS-Chroma vamp 플러그인 macOS arm64 미지원** — autochord 번들 .so가 Linux x86-64. [Vamp Plugin Pack v2.0](https://github.com/vamp-plugins/vamp-plugin-pack/releases/tag/v2.0) DMG (universal binary)로 해결.
7. **새 venv에 setuptools 누락** — `pip install setuptools wheel` 선행 필요.

---

## 7. 직전 상태 / 다음 후보 작업

- **git 작업 트리**: clean (마지막 커밋 `503b823 Update .gitignore`)
- **memo.md**: `1.` 한 줄만 있음 (작업 메모 거의 비어있음)
- **output/**: 비어있음 — 마지막으로 end-to-end 실행해서 산출물을 남기지 않은 상태
- **MEMORY.md / .claude/projects 메모리**: 없음 (이 머신에 누적된 메모리 미생성)

### 자연스러운 다음 단계 후보

(우선순위는 사용자 판단)

1. **end-to-end 동작 검증**
   ```bash
   source venv/bin/activate
   python main.py "유재하-사랑하기 때문에-Acoustic Guitar.mp3"
   ```
   → 추출 코드 진행 출력 → LLM 편곡 → output/ 산출물 생성까지 한번 흘려보기.
2. **백엔드 + 프론트엔드 통합 동작 확인** — 업로드 → POST /api/audio/extract → 프론트에서 결과 표시 흐름.
3. **추출 정확도 평가** — 유재하 곡으로 demucs+autochord가 librosa 대비 얼마나 개선됐는지 정성 비교.
4. **PRD에 명시된 미해결 폴리싱**
   - 마디 단위 묶음/압축 로직이 충분한지
   - LLM 프롬프트 엔지니어링 (편곡 품질)
   - 악보 렌더링 시 마디 분할/박자 표시
5. **memo.md** 정리 (현재 거의 비어있어 의도 파악 어려움)

---

## 8. 새 세션에서 컨텍스트 빠르게 잡는 법

새 Claude Code 세션을 이 폴더에서 열고 다음 순서로 읽으면 됨:

1. **이 파일 (`tbc.md`)** — 전체 핸드오프
2. **[PRD.md](PRD.md)** — 제품 스펙
3. **[issue.md](issue.md)** — 이미 해결된 이슈/함정 (다시 밟지 않기)
4. **[main.py](main.py)** — CLI 진입점부터 흐름 파악
5. **[audio_analysis.py](audio_analysis.py)** — 핵심 파이프라인 (특히 라인 21: `TF_USE_LEGACY_KERAS` 설정 위치)
6. 필요 시 [backend/](backend/), [frontend/](frontend/)

또는 새 세션에서 바로:

> "tbc.md를 읽고 chord_ai 프로젝트 작업을 이어서 도와줘. 다음으로 [원하는 작업]을 하고 싶어."

---

## 9. 주의사항 (다시 밟으면 안 되는 함정)

- **`TF_USE_LEGACY_KERAS=1`은 autochord/TF import 이전에 설정해야 함** — [audio_analysis.py:21](audio_analysis.py#L21)에 `os.environ.setdefault`로 박혀있음. 이 줄을 import 아래로 옮기지 말 것.
- **venv는 Python 3.12** — `venv-py314-backup`은 사용 금지 (TF 미지원).
- **vamp 재설치 시** — `pip install --no-build-isolation vamp` (PEP 517 격리에서 numpy 못 찾음).
- **NNLS-Chroma 플러그인** — `~/Library/Audio/Plug-Ins/Vamp/`에 universal binary `.dylib`이 깔려 있어야 함. 의심되면 `file <path>`로 아키텍처 확인.
- **FastAPI 라우트에서 쿠키 헤더 다룰 때** — `Response`를 직접 만들어 거기에 쿠키 설정 후 반환. 의존성 주입된 `response`는 Pydantic 반환 시에만 유효.

---

## 10. 계정/세션 메모

- 직전 세션은 토큰 소진으로 종료 (다른 계정).
- 현재 세션은 새 계정으로 로그인. 대화 히스토리는 이어지지 않으나 코드/문서/git은 그대로.
- 이 파일이 두 세션 간의 다리 역할.
