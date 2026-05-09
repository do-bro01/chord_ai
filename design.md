## 디자인 레퍼런스

- 전체 무드: Vercel 웹사이트처럼 다크하고 미니멀하고 고급스러운 느낌
- UI 컴포넌트: Apple 제품 소개 페이지처럼 둥글고 부드럽고 절제된 느낌
- 절대 금지: 네온 효과, 사이버펑크 느낌, 과한 그라디언트, 복잡한 애니메이션

## 컬러 팔레트

- 배경: #000000 또는 #0a0a0a
- 카드/컨테이너: #111111 또는 #1a1a1a
- 텍스트 메인: #ffffff
- 텍스트 서브: #888888
- 포인트 컬러: #ffffff (흰색 계열만, 컬러 포인트 없음)
- 테두리: rgba(255,255,255,0.08)

## 타이포그래피

- 폰트: Inter 또는 SF Pro 계열
- 제목은 크고 얇게 (font-weight: 300~400)
- 본문은 작고 깔끔하게

## UI 컴포넌트 스타일

- border-radius: 16px~24px (Apple처럼 둥글게)
- 버튼: 둥근 pill 형태, 배경 흰색/검정 심플하게
- 카드: 얇은 테두리, 미세한 백그라운드 차이로만 구분
- 아이콘: 라인 아이콘 스타일 (lucide 또는 heroicons)
- 그림자: box-shadow 거의 없음, 있어도 아주 미세하게

## 화면 구성

### 인증되지 않은 사용자
1. **로그인 페이지** (`/login`)
   - 중앙 정렬된 미니멀 카드(`#111111`, 둥근 모서리, 얇은 테두리)
   - 로고(chord_ai) → 이메일 입력 → 비밀번호 입력 → "로그인" pill 버튼(흰 배경)
   - 구분선("또는") 아래 "Google로 계속하기" pill 버튼(검정 배경 + 흰 테두리, 좌측 Google 아이콘)
   - 하단 텍스트 링크: "계정이 없으신가요? 회원가입"

2. **회원가입 페이지** (`/signup`) — 3-step 위저드, 같은 카드 레이아웃에서 단계만 교체
   - **Step 1: 이메일 입력**
     - 이메일 입력 → "인증코드 받기" 버튼
     - 상단에 진행 인디케이터(점 3개, 현재 단계만 흰색)
   - **Step 2: 인증코드 + 비밀번호**
     - 6자리 코드 입력(개별 칸 6개, 모노스페이스 느낌)
     - "코드 재전송"(60초 쿨다운 텍스트 카운트다운)
     - 비밀번호, 비밀번호 확인 입력
     - "가입 완료" 버튼
   - **Step 3: 완료**
     - 체크 아이콘 + "환영합니다" → 홈으로 자동 이동

### 인증된 사용자(메인)

> 프로젝트 방향 전환에 따라 메인 흐름이 "코드 입력 → 옵션 선택 → 청음 → 수정 → export"로 재설계됨. 자세한 배경은 [PRD.md](PRD.md) 및 [issue.md](issue.md) 항목 13 참고.

3. **상단 헤더** (`/`, `/arrange` 공통)
   - 로고(chord_ai) + 심플한 네비 + 우측 사용자 아바타(이메일 첫 글자) → 클릭 시 메뉴(로그아웃)

4. **홈 / 입력 화면** (`/`)
   - 두 갈래 진입:
     - **(메인) 코드 직접 입력 카드** — 큰 텍스트박스 또는 마디별 칩 입력. Key/BPM/박자 입력 행. "키 자동 추정" 보조 버튼.
     - **(보조) MP3에서 추출하기 카드** — 작게. 클릭 시 업로드 다이얼로그.
       - 다이얼로그 상단에 **정확도 한계 안내 카피** 명시:
         "추출 결과는 부정확할 수 있으며 sus·9th/11th·CM7 ↔ Em7 같은 모호성은 보정되지 않습니다. 추출 후 직접 수정해서 사용하세요."
   - 입력 완료 → "편곡 시작" pill 버튼 → `/arrange`로 이동.

5. **편곡 워크스페이스** (`/arrange`)
   - **상단 — 코드 차트** (마디별 칩, 클릭하면 인라인 편집).
   - **좌측 패널 — 구조화 옵션**(`OptionPanel`):
     - 장르 / 코드 복잡도 / 텐션 사용량 / 베이스 스타일 / 리듬 성향 — 각각 pill 선택형.
   - **좌측 하단 — 자유 텍스트 보조**(`FreeTextHint`): 1~2줄 placeholder("밤 드라이브 느낌").
   - **우측 상단 — MIDI Preview Player**: 재생/정지, 트랙 표시(피아노·베이스).
   - **우측 하단 — RefineChat**: 사용자 발화("좀 더 재즈스럽게") → state 갱신 → 자동 재편곡·재미리듣기.
   - 하단 bar: "악보 생성" 버튼 (만족 시 export 모달 호출).

6. **Export 모달**
   - MusicXML / MIDI / PDF 각각 다운로드 버튼.
   - 미리보기는 PDF만 (OpenSheetMusicDisplay 등은 v2).

#### MVP에서 제외된 화면 (v2 후보)
- 편곡 변경 이력 시각화, 마디 단위 부분 수정 UI, 풀밴드(드럼·EP) 트랙 토글, 코드 차트 PNG export.

반응형은 일단 데스크탑 기준으로만 만들어줘.

## 배경 효과

- 검정 배경 위에 흰색 점(원)들이 천천히 떠다니는 Canvas 애니메이션 적용
- 점의 크기: 1px~2px, 불규칙하게
- 점의 opacity: 0.3~0.8 사이로 랜덤하게, 깜빡이는 효과 없음
- 움직임: 매우 느리게 랜덤한 방향으로 표류(drift)하는 느낌
- 점의 개수: 150~200개
- 마우스를 가져다대도 반응 없음 (인터랙션 없이 그냥 조용히 흘러가는 느낌)
- 네온 glow 효과 절대 없음, 순수하게 흰 점만
- 모든 페이지(로그인/회원가입/메인)에서 동일하게 표시

---

# 기술 설계: 회원가입/로그인 시스템

프론트는 **Next.js (App Router) + TypeScript + Tailwind CSS**, 백엔드는 **FastAPI 자체 구현**(Supabase 미사용).

## 1. 전체 아키텍처

```
┌──────────────────────────┐         ┌─────────────────────────────────┐
│  Next.js (App Router)    │         │  FastAPI                         │
│  - /login                │  HTTPS  │  - /auth/*  (회원/로그인/OAuth)  │
│  - /signup (3-step)      │ ──────► │  - /api/*   (코드 추출/편곡 등) │
│  - /auth/callback/google │         │  - SQLAlchemy + SQLite           │
│  - 토큰: httpOnly 쿠키   │ ◄────── │  - SMTP(이메일 발송)             │
└──────────────────────────┘         └─────────────────────────────────┘
                                              │
                                              ▼
                                     audio_analysis.py
                                     llm_arranger.py
                                     score_generator.py
                                     audio_renderer.py
```

- **모놀리식 로컬 실행**: 같은 머신에서 `uvicorn` + `next dev` 동시 실행
- **세션**: 서버 발급 JWT를 `httpOnly` `Secure` `SameSite=Lax` 쿠키에 저장 (프론트는 토큰을 직접 다루지 않음)
- **CORS**: dev에서 `http://localhost:3000` ↔ `http://localhost:8000` 허용, `credentials: true`

## 2. 디렉토리 구조 (확장)

```
chord_ai/
├── backend/                       # FastAPI 앱
│   ├── main.py                    # FastAPI entry, 라우터 등록, CORS
│   ├── config.py                  # pydantic-settings 기반 환경변수
│   ├── db/
│   │   ├── database.py            # engine, SessionLocal, get_db
│   │   └── models.py              # User, EmailVerification
│   ├── auth/
│   │   ├── routes.py              # /auth/signup/*, /auth/login, /auth/google/*
│   │   ├── service.py             # 비즈니스 로직 (코드 발급/검증, 사용자 생성)
│   │   ├── security.py            # bcrypt 해싱, JWT 발급/검증
│   │   ├── email_sender.py        # SMTP로 인증코드 메일 발송
│   │   ├── google.py              # Google OAuth 코드 교환·user info 조회
│   │   ├── schemas.py             # Pydantic 요청/응답 모델
│   │   └── deps.py                # get_current_user 의존성
│   └── api/
│       └── chord_routes.py        # 기존 모듈을 HTTP로 노출 (다음 단계)
│
├── frontend/                      # Next.js 앱 (App Router + TS + Tailwind)
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (auth)/signup/page.tsx        # 3-step 위저드
│   │   ├── auth/callback/google/page.tsx
│   │   ├── layout.tsx
│   │   └── page.tsx                       # 홈(보호 라우트)
│   ├── components/
│   │   ├── BackgroundCanvas.tsx           # 흰 점 표류 애니메이션
│   │   ├── auth/EmailStep.tsx
│   │   ├── auth/CodeStep.tsx
│   │   ├── auth/PasswordStep.tsx
│   │   └── ui/*                           # shadcn/ui 베이스
│   ├── lib/
│   │   ├── api.ts                         # fetch 래퍼 (credentials: 'include')
│   │   └── auth.ts                        # 클라이언트 측 헬퍼
│   ├── middleware.ts                      # 보호 라우트 게이트 (쿠키 존재 여부)
│   └── ...
│
├── audio_analysis.py              # (기존)
├── llm_arranger.py                # (기존)
├── score_generator.py             # (기존)
├── audio_renderer.py              # (기존)
├── main.py                        # (기존 CLI — 그대로 유지)
└── chord_ai.db                    # SQLite (gitignore)
```

CLI(`main.py`)는 그대로 두고, 웹 백엔드는 별도 진입점(`backend/main.py`)으로 둔다.
기존 Python 모듈은 동일 프로세스에서 import해서 재사용.

## 3. 데이터베이스

### 선택
- **SQLite** (`chord_ai.db`). 로컬 단일 사용자 환경에 충분.
- **SQLAlchemy 2.0** ORM + **Alembic** 마이그레이션.

### 스키마

#### `users`
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | UUID (PK) | `uuid4` |
| `email` | TEXT UNIQUE NOT NULL | 소문자 정규화 |
| `password_hash` | TEXT NULL | OAuth 전용 사용자는 NULL |
| `provider` | TEXT NOT NULL | `"email"` 또는 `"google"` |
| `provider_subject` | TEXT NULL | Google `sub` 값 |
| `email_verified_at` | TIMESTAMP NULL | 이메일 가입 완료 시점, OAuth는 즉시 |
| `created_at` | TIMESTAMP NOT NULL | |
| `updated_at` | TIMESTAMP NOT NULL | |

- 인덱스: `email` UNIQUE, `(provider, provider_subject)` UNIQUE
- 같은 이메일이 양쪽으로 가입되는 경우: **이메일 기준 단일 사용자**로 통합. Google 로그인 시 기존 이메일 계정에 `provider_subject` 연결.

#### `email_verifications`
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | UUID (PK) | |
| `email` | TEXT NOT NULL | 인덱스 |
| `code_hash` | TEXT NOT NULL | bcrypt로 해싱한 6자리 코드 |
| `purpose` | TEXT NOT NULL | `"signup"` (추후 `"password_reset"`도 동일 테이블) |
| `expires_at` | TIMESTAMP NOT NULL | 발급 시각 + 10분 |
| `consumed_at` | TIMESTAMP NULL | 검증 성공 시 채움 |
| `attempts` | INTEGER NOT NULL DEFAULT 0 | 실패 시도 카운트 |
| `created_at` | TIMESTAMP NOT NULL | |

- 같은 `(email, purpose)`로 새 코드 발급 시 기존 미소비 레코드는 무효화(`consumed_at = now()`).
- 검증 조건: `expires_at > now()` AND `consumed_at IS NULL` AND `attempts < 5` AND `bcrypt.checkpw(code, code_hash)`.

## 4. 회원가입 플로우 (이메일 + 인증코드)

```
[Step 1: 이메일 입력]
  사용자가 이메일 입력 → "인증코드 발송"
                   │
                   ▼
  POST /auth/signup/request-code  { email }
                   │
                   ▼
  - 이메일 형식 검증
  - 이미 가입된 이메일이어도 200 반환 (정보 노출 방지: 동일 응답)
  - 6자리 코드 생성 → bcrypt 해시 저장
  - SMTP로 발송
                   │
                   ▼
[Step 2: 인증코드 + 비밀번호]
  사용자가 코드 6자리, 비밀번호, 비밀번호 확인 입력
                   │
                   ▼
  POST /auth/signup/verify  { email, code, password }
                   │
                   ▼
  - 코드 검증 (만료/소비/시도 횟수)
  - 비밀번호 정책 검증
  - 사용자 생성 (provider="email", email_verified_at=now)
  - JWT 발급 → httpOnly 쿠키 Set-Cookie
                   │
                   ▼
[Step 3: 가입 완료] → 홈(/)으로 리다이렉트
```

### 비밀번호 정책 (백엔드 검증)
- 최소 8자, 최대 72자 (bcrypt 한계)
- 영문 + 숫자 포함 (특수문자는 권장이지만 강제하지 않음)
- v1에서는 길이/문자종류만 검증

### 클라이언트 추가 검증
- "비밀번호 확인" 일치는 프론트에서만 확인 (서버는 단일 `password` 필드만 받음)

### 인증코드 정책
- **6자리 숫자** (`secrets.choice("0123456789")` 6번)
- TTL **10분**
- 재발송 쿨다운 **60초**
- 최대 시도 **5회** 후 코드 무효화

## 5. 로그인 플로우

```
POST /auth/login  { email, password }
        │
        ▼
- 사용자 조회 (password_hash IS NOT NULL)
- bcrypt.checkpw
- 성공 → JWT 발급, httpOnly 쿠키 설정
- 실패 → 401 (이메일/비밀번호 구분 없는 동일 메시지)
```

레이트 리밋: `email` 단위로 분당 10회, IP 단위로 분당 30회.

## 6. Google OAuth 플로우

서버 주도 Authorization Code Flow. 클라이언트 시크릿은 백엔드에만 보관.

```
[프론트] 사용자가 "Google로 계속하기" 클릭
        │
        ▼ window.location = /auth/google/start
[백엔드]
  - state 토큰 생성, httpOnly 쿠키에 저장
  - Google authorize URL로 302 리다이렉트
        │
        ▼ Google 사용자 동의
        │
        ▼ GET /auth/google/callback?code=...&state=...
[백엔드]
  - state 쿠키 검증
  - code → access_token + id_token 교환
  - id_token 검증 (issuer, aud, exp, sub)
  - email, sub 추출
  - 기존 사용자 조회:
      · email 존재 → provider_subject 연결, 로그인 처리
      · 없음 → 신규 사용자 생성 (provider="google", email_verified_at=now)
  - JWT 발급 → httpOnly 쿠키
  - 프론트 홈(/)으로 302 리다이렉트
```

### Google Cloud Console 설정
- OAuth 2.0 Client ID (Web application) 생성
- **Authorized redirect URIs**: `http://localhost:8000/auth/google/callback` (dev)
- **Scopes**: `openid email profile`

### 의존성
- `httpx`로 토큰 교환
- id_token 검증: `google-auth` 라이브러리

## 7. 세션/토큰 전략

- **JWT (HS256)**, 페이로드: `{ sub: user_id, email, iat, exp }`
- 만료: **access 24h** (단일 토큰, 단순화). 추후 refresh 토큰 추가 가능
- 저장: **httpOnly 쿠키**
  - `Name=chord_ai_session`
  - `HttpOnly; Secure; SameSite=Lax; Path=/`
  - dev에서는 `Secure` 생략(또는 https-localhost)
- 로그아웃: `POST /auth/logout` → 쿠키 만료
- 보호 라우트: FastAPI 의존성 `get_current_user`가 쿠키 → 토큰 디코드 → 사용자 조회. 실패 시 401
- 프론트 게이팅: Next.js `middleware.ts`가 쿠키 존재 유무로 리다이렉트 (실제 검증은 서버에서)

## 8. 이메일 발송

### 선택: SMTP (Gmail App Password)
- 무료, 즉시 사용 가능. 운영 단계에서는 SendGrid/Resend로 교체 권장
- 일 발송 한도 500

### 환경변수
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=app_password_16_chars
SMTP_FROM=Chord AI <your_email@gmail.com>
```

### 메일 본문 (한글)
```
제목: [Chord AI] 이메일 인증코드
본문:
  Chord AI 회원가입 인증코드입니다.
  인증코드: 123456
  이 코드는 10분간 유효합니다.
```

## 9. API 명세

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/signup/request-code` | `{ email }` | `204` (성공/이미가입 동일) |
| POST | `/auth/signup/verify` | `{ email, code, password }` | `200 { user }` + 쿠키 |
| POST | `/auth/login` | `{ email, password }` | `200 { user }` + 쿠키 |
| POST | `/auth/logout` | — | `204` (쿠키 삭제) |
| GET | `/auth/me` | — | `200 { user }` 또는 `401` |
| GET | `/auth/google/start` | — | `302` to Google |
| GET | `/auth/google/callback` | `?code&state` | `302` to `/` + 쿠키 |

에러 응답 포맷:
```json
{ "detail": { "code": "INVALID_CODE", "message": "인증코드가 올바르지 않거나 만료되었습니다." } }
```

코드 규칙(예시):
`EMAIL_INVALID`, `CODE_INVALID`, `CODE_EXPIRED`, `CODE_TOO_MANY_ATTEMPTS`, `WEAK_PASSWORD`, `EMAIL_TAKEN`, `INVALID_CREDENTIALS`, `RATE_LIMITED`, `OAUTH_FAILED`

## 10. 환경변수 (전체)

`backend/.env`:
```
APP_ENV=dev
APP_PORT=8000
FRONTEND_ORIGIN=http://localhost:3000

DATABASE_URL=sqlite:///./chord_ai.db

JWT_SECRET=change_me_to_a_long_random_string
JWT_ALG=HS256
JWT_EXPIRE_HOURS=24

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=app_password
SMTP_FROM=Chord AI <your_email@gmail.com>

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

OPENAI_API_KEY=...
```

`frontend/.env.local`:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## 11. 보안 체크리스트

- [x] 비밀번호: bcrypt(cost=12)
- [x] 인증코드: 평문 저장 금지, bcrypt 해시
- [x] 사용자 열거 방지: `request-code`는 항상 동일 응답
- [x] 레이트 리밋: 코드 요청·로그인
- [x] CSRF: SameSite=Lax 쿠키 + 상태 변경 API는 `Origin` 헤더 검증
- [x] OAuth state 토큰 검증
- [x] OAuth id_token 검증 (issuer, aud, exp, sub)
- [x] 비밀번호/시크릿: 로그에 출력 금지

## 12. 추가 의존성

### 백엔드 (pip)
```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
alembic
pydantic-settings
bcrypt
pyjwt
httpx
google-auth
email-validator
```

### 프론트엔드 (npm)
```
next, react, react-dom
typescript
tailwindcss
@radix-ui/react-* (shadcn/ui base)
zod, react-hook-form
lucide-react
```

## 13. 구현 순서

1. `backend/` 스캐폴딩: FastAPI 앱, settings, DB, User/EmailVerification 모델, Alembic 초기 마이그레이션
2. `auth/security.py` (bcrypt, JWT) + `auth/email_sender.py` (SMTP)
3. 회원가입 API 2종 (`request-code`, `verify`) + `login`/`logout`/`me`
4. Google OAuth (`/auth/google/start`, `/auth/google/callback`)
5. `frontend/` 스캐폴딩: Next.js + Tailwind + shadcn/ui + 배경 Canvas
6. `/login`, `/signup` 3-step 위저드, OAuth 버튼, `middleware.ts` 보호
7. e2e 수동 테스트: 이메일 가입→로그인→로그아웃, Google 가입→로그인
8. (다음 단계) 기존 코드 추출/편곡 모듈을 `/api/*`로 노출하고 보호 라우트로 통합

## 14. 결정 사항 메모

- **Supabase 미사용** → 이메일 OTP·OAuth·DB·세션 모두 직접 구현
- **JWT는 단일 토큰(access only)**, refresh 토큰은 v1에서 생략
- **SQLite + Alembic**으로 시작, 운영 시 Postgres로 마이그레이션 계획
- **httpOnly 쿠키 세션** 채택 (XSS로 토큰 탈취 방지)
- **CLI(`main.py`) 유지**, 웹은 `backend/main.py`로 별도 진입점
