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

## 정리: 같은 종류 이슈가 다시 오면 봐야 할 곳

1. **인증/세션 안 됨** → FastAPI에서 `Response`를 직접 반환하는지 vs Pydantic 반환하는지 확인. 둘이 헤더 처리 방식 다름.
2. **`pip install` 빌드 실패** → numpy/setuptools가 빌드 격리에 없는지 의심. `--no-build-isolation` 시도.
3. **TF/PyTorch 설치 불가** → Python 마이너 버전 vs 라이브러리 wheel 지원 매트릭스 확인.
4. **Keras 모델 로딩 실패** → TF 2.16 이후 Keras 3 도입. `tf-keras` + `TF_USE_LEGACY_KERAS=1`.
5. **native plugin 인식 안 됨** → `file <path>`로 아키텍처 먼저 확인. macOS arm64 wheel/binary가 빠진 경우가 잦다.
6. **알고리즘 결과가 별로** → 알고리즘의 표현력(어떤 출력을 표현 가능한가)과 입력 신호 품질을 분리해서 본다. 둘 중 어디가 진짜 병목인지 먼저 파악.
