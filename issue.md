# 개발 중 만난 이슈와 해결 기록

학습용 정리. 시간순서대로, 각 이슈는 "원래 계획 → 발생한 문제 → 원인 → 해결" 형식.

---

## 1. 로그아웃 버튼이 동작하지 않음

**원래 계획**
프론트엔드에서 로그아웃 버튼 클릭 → `POST /auth/logout` → 백엔드가 세션 쿠키 삭제 → 프론트가 `/login`으로 이동.

**발생한 문제**
버튼을 눌러도 사용자가 여전히 로그인 상태로 남았다. `setUser(null)` 등 프론트 상태 초기화를 추가해도 새로고침하면 다시 로그인 상태로 돌아갔다.

**원인**
FastAPI 라우트의 패턴 미스. logout 핸들러가 이렇게 생겼었다:

```python
@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    _clear_session_cookie(response)             # ← 의존성으로 주입된 response에 쿠키 삭제 헤더
    return Response(status_code=204)            # ← 그러나 새 Response를 만들어 반환 → 헤더 유실
```

FastAPI에서 `response: Response`는 **JSON 결과를 자동으로 만들어줄 때**의 응답에 접근하는 통로다. 그런데 함수가 직접 `Response()` 객체를 반환하면 그 객체가 실제 응답으로 나가고, 의존성으로 받은 `response`는 버려진다. 그래서 `Set-Cookie: chord_ai_session=; Max-Age=0` 헤더가 클라이언트에 도달하지 못했다.

**해결**
반환할 Response 객체를 먼저 만들고, 거기에 쿠키 삭제를 설정한다.

```python
@router.post("/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    _clear_session_cookie(response)
    return response
```

**배운 점**
- `response: Response` 의존성은 **Pydantic 모델을 반환할 때만** 의미가 있다.
- `Response`를 직접 만들어 반환하면 의존성 주입 `response`는 무시된다.
- `login`/`signup_verify`는 Pydantic 모델을 반환해서 같은 패턴으로 잘 동작했고, **logout만** 이 함정에 빠져있었다.

---

## 2. 코드 추출 정확도 부족 → 알고리즘 자체 변경

**원래 계획**
`librosa.feature.chroma_cqt`로 크로마 추출 → 24개 코드 템플릿(메이저 12 + 마이너 12)과 코사인 유사도 비교 → 마디 단위로 코드 결정. 외부 의존성 적고 빠르고 단순하다는 장점.

**발생한 문제**
실제 곡(유재하 - 사랑하기 때문에 어쿠스틱)으로 돌려보니 추출 결과가 곡의 실제 진행과 한참 어긋남.

**원인 분석**
구조적 한계가 여러 겹이었다:

| 한계 | 영향 |
|---|---|
| 24개 템플릿(maj/min)만 인식 | 7th, sus, dim, slash 코드 전부 maj/min로 뭉개짐 |
| 보컬·드럼·베이스가 크로마에 같이 섞임 | 화성과 무관한 피치가 노이즈로 작용 |
| 비트 추적 실패 시 결과 통째로 뒤틀림 | 템포 변화/루바토에 약함 |
| 마디 단위 평균 → 마디 안에서 코드 변경 시 한쪽 묻힘 | 코드 체인지가 빠른 곡에서 누락 |
| 인접 코드 평활화(HMM/Viterbi) 없음 | 한두 박자만 어긋난 코드 그대로 출력 |

**해결 (계획 변경)**
3가지 옵션 중 **demucs + autochord** 조합으로 전환.

| 방식 | 정확도 | 속도(3분곡) | 인식 코드 |
|---|---|---|---|
| 현재 (librosa 템플릿) | 매우 낮음 | ~2초 | 24개 |
| autochord 단독 | 높음 | ~10초 | maj/min/7/maj7/min7 등 |
| demucs + autochord | 매우 높음 | ~30~60초 | 좌동 (보컬·드럼 노이즈 제거) |

- **demucs**: Facebook의 음원 stem 분리 모델 (htdemucs). 보컬/드럼/베이스/기타로 4채널 분리. PyTorch + Apple Silicon MPS 가속.
- **autochord**: BTC(Bidirectional Transformer for Chord Recognition) 모델. NNLS-Chroma 입력 → BiLSTM-CRF 분류.

**배운 점**
- 정확도 한계는 종종 **알고리즘 자체의 표현력 부족**이 원인이다 — 템플릿 24개로는 7th 한 종류도 표현 못 한다.
- "노이즈가 많아 보이면 노이즈를 빼라" — 보컬·드럼이 화성 인식에 노이즈로 작용. demucs로 사전 분리하면 입력 신호 품질이 근본적으로 달라진다.

---

## 3. Python 3.14에선 TensorFlow 설치 불가

**원래 계획**
이미 만들어진 venv(Python 3.14)에 `pip install demucs autochord tensorflow torch`로 끝.

**발생한 문제**
`pip install tensorflow` → `ERROR: No matching distribution found for tensorflow`.

**원인**
TensorFlow는 Python 마이너 버전마다 wheel을 따로 빌드해서 PyPI에 올린다. **Python 3.14는 너무 최신이라 TF wheel이 아직 없음** (TF 2.21 기준 3.9~3.13까지 지원).

`pip index versions tensorflow`로 사용 가능한 버전 조회해보면 3.14에서는 "No matching distribution"이 뜬다. 즉 TF 측에서 안 만들어 둔 것.

**해결**
venv를 Python 3.12로 재생성.

```bash
mv venv venv-py314-backup                  # 기존 백업
~/.local/bin/python3.12 -m venv venv       # 3.12로 새로 생성
source venv/bin/activate
pip install -r requirements.txt
```

**배운 점**
- ML/오디오 라이브러리 스택(특히 TF, PyTorch)은 **Python 마이너 버전 호환에 매우 보수적**이다. 최신 Python을 쓰면 wheel 미지원으로 막히는 경우가 흔함.
- 새 프로젝트 시작할 때 Python 버전은 **사용할 라이브러리들이 모두 wheel을 제공하는 가장 최신 버전**으로 선택하는 게 안전. 보통 최신 -1 또는 -2.

---

## 4. `vamp` 패키지 빌드 실패 (PEP 517 격리 환경에서 numpy 못 찾음)

**원래 계획**
`pip install -r requirements.txt` 한 번으로 전부 설치.

**발생한 문제**
```
ERROR: Failed to build 'vamp' when getting requirements to build wheel
ModuleNotFoundError: No module named 'numpy'
```

**원인**
`vamp` 패키지는 prebuilt wheel이 없어서 source에서 빌드해야 한다. 빌드 시 `setup.py`가 numpy를 import해서 buld config을 만든다.

그런데 modern pip은 **PEP 517 build isolation**을 기본 사용한다 — 빌드용 임시 환경을 따로 만들어서 거기서 빌드를 진행하는데, 이 격리 환경엔 호스트 venv의 패키지가 안 들어간다. 그래서 numpy가 없어서 빌드 실패.

**해결**
1. 호스트 venv에 numpy + setuptools + wheel 먼저 설치
2. `vamp`만 `--no-build-isolation`으로 따로 설치 (호스트 환경의 numpy 사용)
3. 그 다음 나머지 requirements 설치

```bash
pip install numpy Cython setuptools wheel
pip install --no-build-isolation vamp
pip install -r requirements.txt
```

**배운 점**
- `pip install` 빌드 실패 시 첫 번째 의심: **PEP 517 isolation에 빌드 의존성이 없는가?**
- 해결책: 빌드 의존성을 미리 깔고 `--no-build-isolation` 플래그 사용. 또는 `pyproject.toml`의 `[build-system].requires`에 빌드 의존성을 명시 (단 패키지 작성자 영역).
- `setup.py`에서 `import numpy` 하는 옛날 패키지들이 종종 이 문제를 일으킨다.

---

## 5. autochord 모델 로딩 실패 (Keras 2 SavedModel ↔ Keras 3 호환성)

**원래 계획**
TF 2.21 + autochord 0.1.4 그냥 import.

**발생한 문제**
```
Exception: autochord: Error in loading model:
File format not supported: filepath=/Users/do_bro/.autochord/chroma-seq-bilstm-crf-v1/.
Keras 3 only supports V3 `.keras` files, legacy H5 format files (`.h5` extension).
Note that the legacy SavedModel format is not supported by `load_model()` in Keras 3.
```

**원인**
- autochord는 오래된 패키지. 모델을 **TensorFlow SavedModel 디렉토리** 형식으로 저장해 배포했음.
- TF 2.16부터 기본 Keras가 **Keras 3**으로 바뀜. Keras 3는 Keras 2의 레거시 SavedModel을 못 읽는다 (`.keras` v3 또는 `.h5`만 지원).
- 결과: TF 2.21 + autochord 조합에서 모델 로딩 실패.

**해결**
공식 마이그레이션 경로: **`tf-keras` 패키지 설치 + `TF_USE_LEGACY_KERAS=1` 환경변수**.

- `tf-keras`는 Keras 2 호환성을 위한 별도 PyPI 패키지.
- `TF_USE_LEGACY_KERAS=1`을 TF import **이전에** 설정하면 TF가 Keras 3 대신 tf-keras (Keras 2)를 사용한다.

```bash
pip install tf-keras
TF_USE_LEGACY_KERAS=1 python -c "import autochord; ..."
```

코드 안에서 설정할 때는 import보다 먼저:
```python
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import autochord  # 이 순서가 중요
```

**배운 점**
- 메이저 라이브러리(TF의 Keras처럼)가 메이저 업그레이드를 하면 의존하던 패키지들이 줄줄이 깨진다.
- Keras 3 도입은 TF 2.16 이후의 큰 변화. 옛 모델 자산은 자동 변환 안 됨.
- 환경변수 기반 호환 모드는 **import 시점 이전**에 세팅해야 효과가 있다 (라이브러리가 import 시 분기 결정하기 때문).

---

## 6. NNLS-Chroma vamp 플러그인 macOS arm64 미지원

**원래 계획**
autochord가 패키지 안에 번들로 포함한 `.so` 파일을 `~/Library/Audio/Plug-Ins/Vamp/`에 복사하면 끝.

**발생한 문제**
복사했는데도 vamp가 플러그인을 인식 못 함. `vamp.list_plugins()` 결과가 빈 리스트 `[]`.

**원인 추적**
파일 자체를 살펴봤다:
```
$ file ~/Library/Audio/Plug-Ins/Vamp/nnls-chroma.so
ELF 64-bit LSB shared object, x86-64, ... (Linux 바이너리)
```

autochord 패키지에 번들된 `.so`가 **Linux x86-64 ELF 바이너리**. macOS는 Mach-O 형식을 쓰고, 이 환경은 **Apple Silicon arm64**. 양쪽 다 안 맞음. autochord 메인테이너가 Linux 빌드만 번들한 듯.

**해결**
공식 [Vamp Plugin Pack v2.0](https://github.com/vamp-plugins/vamp-plugin-pack/releases/tag/v2.0) DMG 사용.

- 빌드 스크립트가 `archs="x86_64 arm64"` 명시 → **universal binary**
- NNLS-Chroma 포함 (`nnls-chroma.pro` 파일 존재)
- DMG 다운로드 → 마운트 → 인스톨러 GUI 실행 (silent install 옵션 없음, 1번 클릭)
- 인스톨러가 `~/Library/Audio/Plug-Ins/Vamp/`에 universal 바이너리 .dylib 설치

**배운 점**
- Python 패키지가 native binary를 번들할 때 **모든 OS/arch 조합을 커버하는지 확인** 필요. 특히 Apple Silicon(arm64)은 종종 누락된다.
- 의심될 때 첫 진단: `file <binary_path>` → 아키텍처와 포맷이 맞는지.
- vamp 같은 플러그인 시스템은 호스트 OS의 동적 라이브러리 형식(.so / .dylib / .dll)을 그대로 사용하므로, 크로스 플랫폼 배포가 까다롭다.

---

## 7. 빌드 도구 누락 (setuptools)

**원래 계획**
새 venv에 numpy 설치 → vamp 빌드.

**발생한 문제**
```
pip._vendor.pyproject_hooks._impl.BackendUnavailable:
Cannot import 'setuptools.build_meta'
```

**원인**
새로 만든 venv에 `pip`만 있고 `setuptools`/`wheel`이 없음. 옛날 Python venv는 setuptools가 기본으로 들어있었지만 최근 버전(3.12+)부터는 venv 생성 시 setuptools를 자동으로 안 깔아줄 수 있다.

**해결**
```bash
pip install setuptools wheel
```

**배운 점**
- 새 venv 만들면 일단 `pip install setuptools wheel`을 먼저 깔자. 빌드 의존성에 거의 항상 필요.
- numpy/Cython 같은 빌드 시간 의존성과 함께 묶어서 첫 한 줄로 처리:
  ```bash
  pip install --upgrade pip setuptools wheel numpy Cython
  ```

---

## 8. 코드 추출 정확도 한계 (2차) → autochord → chordino 전환

**원래 계획**
demucs + autochord 조합으로 24개 코드(maj/min/7/maj7/m7/dim/aug/sus 등) 인식. 7th 텐션도 잡힐 거라 기대.

**발생한 문제**
유재하 - 사랑하기 때문에 어쿠스틱으로 평가하니 **autochord가 7th 텐션을 한 번도 출력 안 함**. 모든 코드가 maj/min 트라이어드로만 나옴(108 segments 중 maj7/m7/7 라벨 0개). 또 일관된 substitution 오류:
- `CM7` 자리에서 `Em` 출력 (상부구조 공유 EGB)
- `Bm7` 자리에서 `Em` 또는 `D` 출력
- `E7(#5)` 자리에서 `D` 또는 `Em` 출력

**원인**
autochord의 BTC(Bidirectional Transformer for Chord Recognition) 모델은 라벨셋 자체에 7th을 갖고 있지만, 학습 데이터 분포가 트라이어드 위주여서 실제 추론 시에는 7th을 거의 안 뱉는 경향. K-pop 발라드처럼 7th 위주 화성은 표현력이 모자람.

**해결**
같은 곡에 **chordino(NNLS-Chroma vamp 플러그인) 적용**. chordino의 강점:
- `usehartesyntax=1` 옵션으로 `C:maj7`, `A:min7`, `D:7` 같은 Harte 표기 직접 출력
- E7(#5)은 `Eaug`로 잡음(공유 음 G#-C가 augmented triad와 일치)
- maj7/m7/7/sus2/sus4/dim/aug 등 풍부한 quality 라벨

같은 곡에서 비교:
| 지표 | autochord | chordino |
|---|---|---|
| 코드 종류 수 | 10 (maj/min만) | 30+ |
| 7th 텐션 검출 | 0% | 다수 정확 |
| E7(#5) | ✗ (D로 오인) | ✓ (Eaug) |

**부작용 + 후속 처리**
chordino도 비다이어토닉 잡음(`Bm7b5`, `Am7b5`, `Bbm6`, `F#aug`)을 새로 만들어냄. 키 감지(qm-keydetector) + 다이어토닉 보정으로 해결. "비다이어토닉 + 짧은 segment(<3s)"만 가까운 다이어토닉으로 스냅하고, secondary dominant(E7, A7, G7 등) borrowed 코드는 보존하는 규칙.

**배운 점**
- 딥러닝 모델의 라벨셋 ≠ 실제 출력 분포. 어휘를 가졌다고 다 잡지 않음.
- 알고리즘마다 노이즈 패턴이 다름. chordino는 "비다이어토닉 노이즈"를 만들고, autochord는 "트라이어드 단순화 노이즈"를 만듦.
- 키/장르 사전 지식을 후처리에 주입하면 알고리즘 노이즈를 음악적 룰로 거를 수 있음.

---

## 9. chroma 기반 sus4 검출 시도와 한계

**원래 계획**
사용자 곡에 `Gsus4`가 있음. chordino도 sus4는 잘 못 잡으니까(이 곡에선 `Gsus4` → `G`로 통합), **per-segment chroma 분석**으로 추가 검출 시도. 로직: G로 인식된 segment에서 chroma의 4음(C)이 3음(B)보다 강하면 → Gsus4.

**발생한 문제**
**두 곡 연속 sus4 검출 0개**.
- 유재하 곡: chroma의 G segment에서 C(4음)가 어떤 0.5초 윈도우에서도 B(3음)보다 강하지 않음. 핑거스타일이라 sus → 해결을 빠르게 거치면서 4음이 차분하게 안 깔림.
- Bon Jovi - Wanted Dead or Alive: 사용자 chord chart가 `Dsus4 D Dsus2 D` 패턴인데도 같은 결과. chroma 진단:
  ```
  D = 1.00 (압도적)
  F#(M3) = 0.06~0.18
  G(P4) = 0.04~0.20
  E(P2) = 0.05~0.22
  ```
  12현 어쿠스틱이 D 루트를 옥타브로 쌓아서 다른 음들이 상대적으로 매우 약함.

**원인**
chroma 기반 sus 검출은 "이상적 조건"에서만 동작:
- sus 코드가 sustained(수 초 이상)
- 4음이 다른 음 대비 충분히 voicing됨

실제 녹음에서는 보통:
- sus는 짧게 거치고 해결됨 → 평균 chroma에 묻힘
- 루트가 옥타브 doubling/sustaining으로 압도적 → 상부 음들이 모두 약함

**해결**
**기능 자체 제거**. `sus_detector.py` 삭제. 이상치 걸러내려 추가한 절대 강도 체크(>= 0.4 of root)에서 모든 후보가 제거되니, 모듈 자체가 무용.

**배운 점**
- 음악 이론적으로 명백한 차이("3음 vs 4음")가 신호처리에서는 detect 가능을 보장 안 함.
- 라이브 녹음의 chroma는 의외로 root에 강하게 편향됨 (옥타브 doubling, 베이스 sustain).
- 두 종류 곡(빠른 ballad sus + 12현 strum sus)에서 모두 실패하면, 알고리즘 한계로 인정하고 빨리 제거. "이론상 동작해야 하는" 모듈을 무리해서 유지하면 유지보수 부담만 늘어남.
- Sub-window 분석으로 평균 효과를 줄이는 방법도 가능하지만, 절대 강도 부족이 본질이라 효과 보장 안 됨.

---

## 10. 베이스 음 검출로 상부구조 substitution 정정

**원래 계획**
chordino + 다이어토닉 보정 후에도 남은 핵심 오류:
- `CM7` ↔ `Em7` 모호성 (둘 다 EGB 공유, root만 다름 — C vs E)
- `Bm7` ↔ `D` 모호성 (둘 다 D-F#-A 공유)
- `C/D` 슬래시 코드의 베이스 음 오인

이 셋 모두 **베이스 음이 결정**. demucs가 이미 분리해 놓은 bass stem에서 segment별 dominant pitch를 뽑으면 해결될 거라 가설.

**발생한 문제**
처음 구현 시 너무 aggressive — 신뢰도 1.5 이상 segment에 다 베이스 보정 적용하니 `Em/G`, `G/B`, `Am/D#` 같은 어색한 slash가 다수 등장. 또 인접 코드 transition 부분에서 베이스 음이 흔들려 false positive.

**원인 + 해결**
- 신뢰도 임계값 너무 낮음 → 1.5 → **2.5로 상향**. top1/top2 chroma 비율로 측정.
- 베이스 정정 후 결과가 키의 다이어토닉/borrowed에 들어와야만 채택 (음악적 타당성 게이트)

핵심 정정 룰:
```
chordino "Em7" + 베이스=C → "Cmaj7"      (m7 root - 4 = maj7 root)
chordino "D"   + 베이스=B → "Bm7"        (maj root - 3 = m7 root)
chordino 그 외 + 다른 베이스 → slash 표기 (예: "C/E")
```

같은 곡에서 결과:
- ✅ Bm7 회복 6군데 (chordino "D" → "Bm7")
- ✅ 슬래시 코드 베이스 정정
- ⚠️ CM7 ↔ Em7는 부분적 — 핑거스타일 보이싱이 실제 E를 베이스로 두는 경우도 있어 음악적으로 모호

**배운 점**
- 상부구조 substitution은 **베이스 검출로 결정론적으로 풀 수 있다** (최소 룰 베이스로). 새 의존성 없이 demucs의 기존 출력 활용.
- 음악적 타당성 가드(다이어토닉/borrowed 체크) 없이 raw 베이스 검출만 따라가면 노이즈 다수 도입.
- 핑거스타일 곡에서 베이스가 항상 chord root는 아님 — 실제 녹음의 ambiguity는 알고리즘 한계가 아니라 음악적 모호성.

---

## 11. 라벨 표기 정규화 (Harte 표기 + music21 호환)

**원래 계획**
chordino의 출력을 그대로 다음 단계(LLM 편곡, 악보 생성)로 전달.

**발생한 문제**
chordino의 슬래시 코드 표기가 사용자 친화적이지 않음:
- `C/5` (interval-based: 5도 = G in bass) → 사용자는 `C/G` 로 보고 싶음
- `D/2` (interval-based: 2도 = E in bass) → `D/E` 가 자연스러움

또 music21이 일부 표기를 못 받음:
- `Dmaj6` → `Invalid chord abbreviation 'maj6'`
- `Cmaj9` → `Invalid 'maj9'`
- `mMaj7` → `Invalid 'mMaj7'`

**원인**
- Harte 표기는 학술 chord recognition의 표준이지만 일반 사용자 표기와 다름.
- music21의 `harmony.ChordSymbol` 어휘가 제한적. major 6/9/min-major7 같은 일부 quality는 다른 표기를 요구.

**해결**
`chord_postprocess.normalize_label()` + `chord_to_string()`에 매핑 추가:
```
maj6 → 6        (major 6은 관용적으로 그냥 "6")
maj9 → maj7     (lossy — 9th 손실, music21 미지원)
minmaj7 → mM7   (music21 표기)
C/5 → C/G       (interval → 음 이름 변환)
```

마지막에 모든 segment 라벨을 `normalize_label()` 통과시켜 정규화. 결과: 모든 라벨이 사람이 읽기 쉽고 music21이 파싱 가능.

**배운 점**
- 라이브러리 간 chord 표기 호환성을 미리 확인 안 하면 다음 단계에서 silent fail (악보의 코드가 휴지부로 대체됨).
- "내부 처리 표기" 와 "출력 표기" 분리 — 내부에선 정확한 quality 추적, 출력만 호환 표기로.
- Lossy 매핑이 필요할 때(예: maj9 → maj7) 명시적으로 문서화.

---

## 12. demucs stem 결과 캐싱

**원래 계획**
chordino_extractor와 bass_detector가 각자 demucs를 호출.

**발생한 문제**
demucs 분리는 ~30초 걸림. 두 모듈이 따로 호출하면 같은 곡에 대해 60초. 명백한 낭비.

**해결**
`audio_analysis.py`에 모듈 레벨 dict 캐시 추가:
```python
_separation_cache: dict = {}  # key: f"{path}:{mtime}", value: (stems_dict, sr)

def separate_all_stems(audio_path: Path):
    cache_key = f"{audio_path.resolve()}:{audio_path.stat().st_mtime}"
    if cache_key in _separation_cache:
        return _separation_cache[cache_key]
    # ... demucs 실행 ...
    _separation_cache[cache_key] = (stems, sr)
    return stems, sr
```

같은 process 안에서 모든 모듈이 같은 분리 결과 공유. mtime을 키에 포함해서 파일이 바뀌면 자동 재계산.

**배운 점**
- 무거운 연산 결과를 함수 호출 단위가 아니라 process 단위 캐시로 관리.
- 캐시 키에 mtime 포함하면 파일 변경 시 stale 캐시 자동 무효화.
- 모듈 레벨 dict는 단일 process 캐시로 충분(Backend는 multi-worker라도 worker별 캐시면 OK).

---

## 정리: 같은 종류 이슈가 다시 오면 봐야 할 곳

1. **인증/세션 안 됨** → FastAPI에서 `Response`를 직접 반환하는지 vs Pydantic 반환하는지 확인. 둘이 헤더 처리 방식 다름.
2. **`pip install` 빌드 실패** → numpy/setuptools가 빌드 격리에 없는지 의심. `--no-build-isolation` 시도.
3. **TF/PyTorch 설치 불가** → Python 마이너 버전 vs 라이브러리 wheel 지원 매트릭스 확인.
4. **Keras 모델 로딩 실패** → TF 2.16 이후 Keras 3 도입. `tf-keras` + `TF_USE_LEGACY_KERAS=1`.
5. **native plugin 인식 안 됨** → `file <path>`로 아키텍처 먼저 확인. macOS arm64 wheel/binary가 빠진 경우가 잦다.
6. **알고리즘 결과가 별로** → 알고리즘의 표현력(어떤 출력을 표현 가능한가)과 입력 신호 품질을 분리해서 본다. 둘 중 어디가 진짜 병목인지 먼저 파악.
7. **코드 인식기가 텐션을 안 잡음** → autochord BTC는 라벨셋에 있어도 거의 안 출력. chordino의 Harte syntax(`usehartesyntax=1`)가 더 풍부.
8. **코드 인식기가 잡음 코드를 만듦** → 키 감지(qm-keydetector) + 다이어토닉 보정으로 후처리. "비다이어토닉 + 짧은 segment"만 스냅, borrowed 코드는 보존.
9. **상부구조 substitution(CM7 ↔ Em7 등)** → demucs bass stem + chroma_cqt로 segment별 dominant pitch 추출 후 룰 베이스 정정.
10. **chroma 기반 sus/9 검출** → 이상적 조건에서만 동작. 빠른 패턴 또는 root-dominant 녹음에서는 실패. 두 곡 실패하면 빨리 포기.
11. **chord 라벨이 다음 단계에서 silent fail** → music21 같은 downstream 라이브러리의 어휘 제한 미리 확인. 호환 표기로 매핑.
12. **무거운 연산 중복 호출** → 모듈 레벨 dict 캐시(키에 mtime 포함)로 process 단위 공유.
