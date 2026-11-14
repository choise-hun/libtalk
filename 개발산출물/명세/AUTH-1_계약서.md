# 로그인 (`auth`) 기술 계약서

> 이 파일은 AUTH Feature의 계약서다. Step마다 절을 하나씩 둔다: **AUTH-1(이 판)**, AUTH-2·AUTH-3은 각 Step 직전에 더한다.
> 상태: **D 계약 검토 반영·B1 확정(2026-11-13).** 계약 C1~C7의 기술 검토를 반영했다. A5~A8은 D 추가 답(C-59)으로 확인했다. 구현 계획은 6파트로 재분할했으며 A9는 B 배치 확정(C-60)이다. 이번 작업은 문서·시안까지이며 구현은 시작하지 않는다.
> **2026-11-13 재배치**: `### 계약`(C1~C7)과 `### 구현 계획`(P1~P5) 두 덩어리로 자리만 옮겼다(내용은 그대로). 옛 번호 → 새 번호: §0→C1, §3.1→C2, §3.2→C3, §3.3→C4, §3.4→C5, §4→C6, §6→C7 / §1→P1, §2→P2, §3.5→P3, §5→P4, §7→P5. 템플릿·`prompts/3_구현.md`·`skills/pr-review`도 C/P 번호로 맞췄다(C-59). 남은 옛 문서 참조는 이 대응표로 읽는다.

---

## AUTH-1 가입·로그인

- **담당 역할**: D · **대상 브랜치**: `main`
- **기준 명세서**: 주니어 세부 명세서 없음(D 담당 Step). 대신 아래를 기준으로 쓴다.
  - 코드 레포 `개발산출물/02_요구사항_정의서.md` AUTH-01·USR-01·USR-02, AC-AUTH·AC-ISOLATION (커밋 `9ad84f7`)
  - 코드 레포 `개발산출물/모호점_해소_기록.md` "2026-11-13 계약 전 확인 답변" AUTH-1 + **Q-52**(같은 날 D가 다시 결정한 내용으로 대체됨)
  - 이 절의 "결정" 번호(A1~A9)를 명세서 결정 번호 대신 쓴다
- **기준선**: 코드 레포 `개발산출물/기준선.md`의 `B1` (2026-11-13, 계약 C1~C7·조건부 구현 계획. 구현 착수 허가와는 별개)
- **선행 설계**: 코드 레포 `개발산출물/05_ERD_및_DB설계서.md` §3.1 users·§4, `개발산출물/06_기능_API_정의서.md` §2.1 1~3행·§3
- **작성자**: D (시니어)

> **구현 Claude 필수 지침**:
> 1. 이 계약서의 파일 목록, 시그니처, 에러 코드, 핵심 흐름 골격(의사코드)을 생략하거나 바꾸지 말 것.
> 2. 표에 없는 필드·파라미터·외부 라이브러리를 추가하지 말 것.

### 계약

> 다른 기능이 기대는 약속이다. 주니어 Claude는 이 덩어리만 읽어도 된다. 고치는 커밋은 머리말 `contract:`.

#### C1. 결정 (명세서 결정 대신)

| # | 결정 | 상태 | 근거 |
| :--- | :--- | :--- | :--- |
| A1 | 로그인은 **Supabase Auth**가 맡는다. 앱이 Supabase로 로그인하고, 서버는 자체 토큰을 만들지 않고 **Supabase가 발급한 access JWT만 검증**한다 | 확인 | D 2026-11-13 (Q-52 ①). 11/13 앞선 답변의 "자체 HS256 발급·`token_type` 검사"를 대체 |
| A2 | 제공자는 Google·Apple. **Apple 버튼은 iOS에서만** 보이고, Android·웹은 Google만 보인다 | 확인 | Q-15 해소, D 2026-11-13 (Q-52 ②) |
| A3 | 서버의 JWT 검증은 Supabase **JWKS 공개키**(`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`)로 한다. 허용 알고리즘 `ES256`·`RS256`만(그 밖의 `HS256`·`none`은 거부). 필수 검사: 서명, `iss` = `<SUPABASE_URL>/auth/v1`, `aud` = `authenticated`, `exp`, `sub`(UUID), `role` = `authenticated`. 키 회전은 Supabase가 하고 서버는 공개키를 다시 받아 따라간다 | 확인 | D 2026-11-13 (Q-52 ③), Supabase 문서 "JWT Signing Keys" |
| A4 | 리프레시 토큰은 Supabase가 발급·저장한다. **이 레포는 세션 테이블을 만들지 않는다.** 철회된 세션 거부(AUTH-02)는 AUTH-2에서 JWT의 `session_id`로 Supabase 세션이 살아 있는지 보는 방식으로 정한다 | 확인 | D 2026-11-13 (Q-52 ④) |
| A5 | 서버 DB에는 `users` 한 테이블만 만든다. 기본 키는 Supabase 사용자 id(`sub`)이고, 이메일·이름·제공자 정보는 저장하지 않는다(Supabase `auth` 스키마에만 있다) | 확인 | 02 §3 "이메일·인증 수단은 공개 프로필에서 제외", 개인정보 최소화  · D 2026-11-13 추가 답: "이번에 네 기본값 검토·확정" (C-59) |
| A6 | `users` 행은 앱이 로그인 직후 부르는 `POST /api/v1/auth/session`이 만든다(처음이면 생성, 있으면 그대로). 다른 모든 기능은 `get_current_user`를 쓰고, 행이 없으면 `401 AUTH_NOT_REGISTERED`로 거부한다 | 확인 | 읽기 요청이 행을 만들지 않게 쓰기 지점을 하나로 둠  · D 2026-11-13 추가 답: "이번에 네 기본값 검토·확정" (C-59) |
| A7 | 같은 이메일의 Google·Apple 계정은 Supabase 기본 "자동 연결"을 그대로 둔다(한 사용자로 합쳐짐). Apple의 "이메일 가리기"를 쓰면 다른 이메일이라 별도 사용자가 된다 | 확인 | [Supabase Identity Linking](https://supabase.com/docs/guides/auth/auth-identity-linking)(검증된 이메일 등 Supabase 연결 조건을 그대로 따름, 앱이 이메일로 사용자를 합치지 않음)  · D 2026-11-13 추가 답: "이번에 네 기본값 검토·확정" (C-59) |
| A8 | 앱의 세션 저장은 Supabase React Native 가이드의 방식으로 기기 저장소(네이티브 `AsyncStorage`, 웹 `localStorage`)에 둔다. 암호화 저장(`LargeSecureStore`)은 쓰지 않는다 | 확인 | [Supabase React Native 가이드](https://supabase.com/docs/guides/auth/quickstarts/react-native)의 AsyncStorage 예시. 암호화 저장은 아니며 출시(RELEASE) 전에 다시 본다  · D 2026-11-13 추가 답: "이번에 네 기본값 검토·확정" (C-59) |
| A9 | **후보 B 확정:** 상단 소개·주요 컬러의 현재 책 모양을 로고로 발전시키는 방향, 하단 제공자 버튼. 코드 레포 `개발산출물/시안/AUTH-1_로그인_시안.html`의 B가 기본 선택이며 A·C도 보존 | 확인(확정, C-60) | D 2026-11-13: 미관·앱의 색감·시연에서 텍스트보다 기억에 남는 로고가 이유. 원문은 코드 레포 정리안 §5. 별도 최종 로고 자산은 미제작. 문구·인증 동작은 C3·C6 유지 |

#### C2. 엔드포인트 / 다른 기능이 가져다 쓰는 함수

| 메서드·경로 (`/api/v1` 접두어) | 인증 필요 | 성공 상태 | 날짜 형식 | 목록이면 페이지·정렬 | 같은 요청을 연타·재시도하면 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/session` | 예 (Supabase access JWT, `Authorization: Bearer <jwt>`. `users` 행이 아직 없어도 된다 — `verify_access_token`만 거침) | `200` (처음·두 번째 모두 200, 처음이면 `is_new: true`) | `created_at`: ISO 8601 초 단위, `+09:00`(KST) | N/A (목록 아님) | `200` / `is_new: false`, `users` 행 1개 그대로(동시에 두 번 와도 `ON CONFLICT DO NOTHING`으로 1개) |
| `GET /api/v1/me` | 예 (`get_current_user`) | `200` | `created_at`: 위와 같음 | N/A (목록 아님) | N/A (읽기만, 몇 번 해도 같음) |

주요 함수(엔드포인트가 아닌 것, AUTH-1-P1 `server/app/auth.py`(JWT), AUTH-1-P3(개인 사용자 조회)):

- `@dataclass(frozen=True) class CurrentUser: id: uuid.UUID; session_id: str | None` — 다른 기능이 받는 "로그인한 사용자". `session_id`는 AUTH-2가 쓴다.
- `async def verify_access_token(request: Request) -> CurrentUser` — 헤더 확인·JWT 검증만 한다(DB를 보지 않음). 실패는 `ApiError`(예외 #1~#4).
- `async def get_current_user(request: Request) -> CurrentUser` — **모든 기능의 개인 데이터 엔드포인트가 `Depends(get_current_user)`로 쓴다.** `verify_access_token` 뒤 `users` 행이 있고 `status = 'active'`인지 본다(예외 #5·#6).
- `server/app/db.py`: `async def run_db(engine: Engine, fn: Callable[[Connection], T]) -> T` — `with engine.begin() as conn: return fn(conn)`를 `asyncio.to_thread`로 돌린다(트랜잭션 하나). 연결 실패는 `ApiError(503, "DB_UNAVAILABLE", "데이터베이스에 연결하지 못했어요.")`. 이후 기능도 이 함수를 쓴다.

앱 쪽 함수(AUTH-1-P5):

- `mobile/src/auth/AuthProvider.tsx`: `useAuth(): { status: "loading" | "signedOut" | "signedIn"; userId: string | null; signInWithGoogle(): Promise<SignInResult>; signInWithApple(): Promise<SignInResult> }`, `type SignInResult = { ok: true } | { ok: false; reason: "cancelled" | "failed" | "network" }`
- `mobile/src/auth/apiFetch.ts`: `apiFetch(path: string, init?: RequestInit): Promise<Response>` — `Authorization: Bearer <access_token>`을 붙인다. 응답이 `401 AUTH_EXPIRED`면 `supabase.auth.refreshSession()` 뒤 **한 번만** 다시 보낸다. `401 AUTH_NOT_REGISTERED`면 `POST /api/v1/auth/session` 뒤 **한 번만** 다시 보낸다. 복구 요청이 실패하면 원 요청을 다시 보내지 않고 그 실패를 반환한다. 최초 요청의 복구·재전송은 전체 합계 한 번뿐이다(갱신 후 미등록 등 오류가 바뀌어도 다시 복구하지 않음). 로그인 등록 요청은 raw 전송으로 보내 자기 자신을 재호출하지 않는다. 다시 보내도 실패하면 그 응답을 그대로 돌려준다. **다른 기능의 화면은 서버를 부를 때 이 함수를 쓴다.**

- **서비스 함수 안에서 오류를 올리는 방식(이 계약서에서 처음 정함, 모든 기능 공통)**: `server/app/common.py`에 `class ApiError(Exception)`(`status_code: int, code: str, message: str, detail: str = ""`)를 두고, `main.py`의 처리기가 `error_response(...)`로 바꾼다. 서비스·의존성 함수는 `raise ApiError(401, "AUTH_INVALID", "...")`처럼 올린다. 이후 계약서의 골격도 이 이름을 쓴다.

#### C3. 요청·응답 필드와 화면 문구

| 구분 | 필드/키 | 타입 | 필수 | 설명·고정 문구 (결정 대응) |
| :--- | :--- | :--- | :--- | :--- |
| 요청 헤더 | `Authorization` | `str` | Y | `Bearer <Supabase access JWT>` (A1·A3) |
| 요청 본문 (`POST /auth/session`) | 없음 | — | — | 본문은 읽지 않는다. `user_id` 등을 보내도 무시하고 토큰의 `sub`만 쓴다(불변 조건 4) |
| 응답 (`POST /auth/session`) | `user_id` | `str (UUID)` | Y | 토큰의 `sub` (A5) |
| 응답 (`POST /auth/session`) | `status` | `str` | Y | `"active"` 고정(이 Step에서 다른 값은 응답하지 않음 — 탈퇴는 예외 #6) |
| 응답 (`POST /auth/session`) | `is_new` | `bool` | Y | 이번 요청이 행을 만들었으면 `true` (A6) |
| 응답 (`POST /auth/session`) | `created_at` | `str (ISO 8601, +09:00)` | Y | 행이 처음 만들어진 시각 |
| 응답 (`GET /me`) | `user_id`, `status`, `created_at` | 위와 같음 | Y | `is_new` 없음 |
| 서버 설정 | `SUPABASE_URL` | `str` | `production`에서 Y | 예: `https://<project-ref>.supabase.co`(끝 `/` 없음). 비밀값 아님. `local`·`test`는 빈 값 허용, 비어 있으면 인증 엔드포인트가 예외 #4 |
| 앱 설정 | `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | `str` | Y | publishable 키는 앱에 넣어도 되는 공개 키다(NFR-04의 "비밀값"이 아님). `service_role`·secret 키는 앱·Git에 넣지 않는다 |
| 화면 문구 | 로그인 화면 제목 | — | — | `"동네한권에 로그인"` — 기본값(Claude) |
| 화면 문구 | Google 버튼 | — | — | `"Google로 계속하기"` — 기본값(Claude) |
| 화면 문구 | Apple 버튼 | — | — | `expo-apple-authentication`의 `AppleAuthenticationButton`(유형 `CONTINUE`) — Apple 지침상 공식 버튼을 쓴다 |
| 화면 문구 | 진행 중 | — | — | 버튼 자리에 진행 표시, `accessibilityLabel` `"로그인하는 중"` |
| 화면 문구 | 스모크 화면 상태 줄 | — | — | `"로그인함"` / `"로그인 안 함"` + `"로그인"` 버튼(→ `/login`) |

#### C4. 플랫폼 분기 표 (분기는 모두 `mobile/src/auth/platform.ts` 한 곳)

| 분기 지점 | 공통 처리(기본) | iOS | Android | 웹 | 분기를 모아 둘 곳 | 확인 (웹·Android: 담당 / iOS: D) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Apple 버튼 보이기 | `isAppleSignInAvailable()`이 `false`면 그리지 않는다 | `AppleAuthentication.isAvailableAsync()` 결과 | 항상 `false` | 항상 `false` | `mobile/src/auth/platform.ts` (AUTH-1-P4에서 만듦) | Android·웹에서 Apple 버튼 없음 / iOS에서 버튼 보이고 로그인됨 |
| Apple 로그인 | — | 원본 nonce를 만들고 SHA-256 값을 Apple에 넘긴 뒤 `supabase.auth.signInWithIdToken({ provider: "apple", token, nonce: 원본 })` | N/A (버튼 없음) | N/A (버튼 없음) | 같은 파일 | iOS만 (D) |
| Google 로그인 | `supabase.auth.signInWithOAuth({ provider: "google" })` (PKCE) | `redirectTo: localone://auth-callback`, `skipBrowserRedirect: true` → `WebBrowser.openAuthSessionAsync` → 돌아온 `code`로 `exchangeCodeForSession` | iOS와 같음 | 전체 페이지 이동 → 돌아오면 `detectSessionInUrl: true`가 세션을 잡는다 | 같은 파일 | 웹(좁은 창·넓은 창)·Android에서 로그인 뒤 스모크 화면이 "로그인함" |
| 세션 저장소 | `persistSession: true`, `autoRefreshToken: true` | `AsyncStorage` | `AsyncStorage` | `localStorage`(Supabase 기본) | 같은 파일 | 앱을 껐다 켜도 "로그인함" |
| 앱이 앞으로 올 때 토큰 갱신 | — | `AppState` 변화에 맞춰 `startAutoRefresh()`/`stopAutoRefresh()` | iOS와 같음 | 하지 않음(브라우저가 처리) | 같은 파일 | 백그라운드 1시간 뒤 돌아와도 요청이 `AUTH_EXPIRED`로 끝나지 않음 |

- 표에 없는 분기는 만들지 않는다.

#### C5. 테이블

**`users`** — 역할: `이 서비스의 사용자 한 명(Supabase 사용자와 1:1)` · 소유자 컬럼: `id`(자기 자신) · 담당 마이그레이션: `server/migrations/versions/0001_users.py`(AUTH-1-P2에서 만듦, Alembic 의존성은 P1에서 추가)

| 컬럼 | 타입 | NULL | 기본값 | 키·제약 (PK/FK/UNIQUE/CHECK) | 설명 (결정 대응) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `uuid` | 아니오 | 없음(토큰의 `sub`를 넣는다) | PK | Supabase 사용자 id (A5) |
| `status` | `text` | 아니오 | `'active'` | CHECK `status IN ('active', 'withdrawn')` | 계정 상태(02 §3 "계정 상태"). `withdrawn`은 AUTH-3이 쓴다. 이 Step에서 쓰는 코드는 없고 시험만 직접 넣는다 (예외 #6) |
| `created_at` | `timestamptz` | 아니오 | `now()` | — | 처음 `POST /auth/session` 시각 |

| 삭제 동작 | 값 |
| :--- | :--- |
| 이 테이블의 행을 지울 때 | 이 Step에서는 지우지 않는다. 탈퇴 때 지울지 `withdrawn`으로 둘지는 AUTH-3 계약서에서 정한다 |
| 부모가 지워질 때 | 부모 FK 없음. Supabase `auth.users`에 FK를 걸지 않는다 — 이유: 시험 DB(postgres:17 컨테이너)에는 `auth` 스키마가 없고, Supabase 쪽 사용자 삭제가 이 레포 데이터를 몰래 지우지 않게 한다. Supabase에서 사용자를 지우는 경로는 AUTH-3에서 함께 정한다 |
| 허용하지 않는 값 | `id` 중복 → `ON CONFLICT (id) DO NOTHING`으로 흡수(예외 아님, C2 연타 칸). `status`가 두 값 밖 → CHECK가 거부(앱 경로 없음, 시험 `test_users_status_check`) |
| 행 수준 보안(RLS) | **`ALTER TABLE users ENABLE ROW LEVEL SECURITY`, 정책 없음.** Supabase는 `public` 스키마를 publishable 키로 REST에 열어 두므로, 정책이 없어야 앱이 서버를 거치지 않고 표를 읽지 못한다. 서버는 테이블 소유자 계정으로 붙어 RLS의 영향을 받지 않는다(05 §4 "RLS가 자동 적용된다고 가정하지 않음"). **이후 모든 기능 테이블에 같은 줄을 넣는다** |

- 다른 기능의 개인 데이터 테이블은 소유자 컬럼을 `user_id uuid NOT NULL REFERENCES users(id)`로 둔다(템플릿 예시의 `bigint`가 아님). `ON DELETE` 동작은 AUTH-3 계약서가 정하기 전까지 기본값(`NO ACTION`)으로 둔다.
- 마이그레이션 규칙(이 계약서에서 처음 정함): 파일 이름 `NNNN_<무엇>.py`(4자리 순번), `revision`은 같은 `NNNN`, `downgrade()`를 반드시 쓴다. `env.py`는 `app.settings.get_settings().database_url`을 쓴다(따로 주소를 두지 않음). CI 서버 job은 `pytest` 앞에 `uv run alembic upgrade head`를 돈다.

#### C6. 검증과 에러 처리

예외 번호는 이 계약서의 번호다(주니어 명세서가 없어 02 AC-AUTH·AC-ISOLATION에서 뽑았다).

| 예외 # | 발생 조건 | HTTP 상태 / 에러 `code` | 화면 문구·동작 | 기록 무변경 보장 |
| :--- | :--- | :--- | :--- | :--- |
| #1 | `Authorization` 헤더가 없거나 `Bearer `로 시작하지 않음 | `401` / `AUTH_REQUIRED` | `"로그인이 필요해요."` → 앱은 `/login`으로 | `users` 행 수 그대로 |
| #2 | 서명 불일치, 알고리즘이 `ES256`·`RS256`이 아님(`HS256`·`none` 포함), `iss`·`aud` 불일치, `role` ≠ `authenticated`, `sub`가 UUID가 아님, 형식이 깨짐, 유효한 JWKS에 `kid`가 없음(아래 재조회·cooldown 규칙 적용) | `401` / `AUTH_INVALID` | `"로그인 정보를 확인하지 못했어요. 다시 로그인해 주세요."` → `/login` | `users` 행 수 그대로 |
| #3 | `exp`가 지남(허용 오차 10초 — 기본값(Claude)) | `401` / `AUTH_EXPIRED` | 앱은 문구 없이 갱신 뒤 한 번 재시도(`apiFetch`). 재시도도 실패하면 #2 문구 | `users` 행 수 그대로 |
| #4 | JWKS HTTP 조회의 timeout(각 조회 3초), 연결 실패, JSON·키 집합 응답이 깨짐, `SUPABASE_URL`이 비어 있음 | `503` / `AUTH_UNAVAILABLE` | `"로그인 확인이 잠시 안 돼요. 잠시 뒤 다시 시도해 주세요."` + 다시 시도 버튼. **로그인 성공으로 표시하지 않는다** | `users` 행 수 그대로 |
| #5 | 토큰은 맞지만 `users` 행이 없음(`get_current_user`) | `401` / `AUTH_NOT_REGISTERED` | 앱은 문구 없이 `POST /auth/session` 뒤 한 번 재시도(`apiFetch`) | `users` 행 수 그대로(`get_current_user`는 행을 만들지 않음) |
| #6 | `users.status = 'withdrawn'` (`POST /auth/session`·`get_current_user` 모두) | `403` / `ACCOUNT_WITHDRAWN` | `"탈퇴한 계정이에요."` — 기본값(Claude), AUTH-3이 다시 볼 수 있음 | 그 행의 `status`·`created_at` 그대로, 행 수 그대로 |
| #7 | DB 연결 실패 | `503` / `DB_UNAVAILABLE` | `"데이터베이스에 연결하지 못했어요."`(기존 `ready`와 같은 문구) | 트랜잭션 안에서 실패 → 쓰인 것 없음 |
| #8 | 다른 사람의 id를 본문·쿼리로 보냄 | (거부하지 않음) `200` | — | 토큰의 `sub` 행만 생기거나 읽힌다. 보낸 id의 행은 생기지 않음 |
| #9 | (앱) 사용자가 Google·Apple 창을 닫음 | — | 문구 없이 로그인 화면에 그대로. 버튼 다시 누를 수 있음 | 저장된 세션 없음 |
| #10 | (앱) 제공자·Supabase 오류 | — | `"로그인하지 못했어요. 다시 시도해 주세요."` | 저장된 세션 없음 |
| #11 | (앱) 네트워크 없음·서버 연결 실패 | — | `"서버에 연결하지 못했어요."`(기존 스모크 화면과 같은 문구) | Supabase 로그인이 됐어도 `POST /auth/session`이 실패하면 "로그인함"으로 바꾸지 않고, 다음 요청 때 `apiFetch`가 #5 경로로 다시 만든다 |
| #12 | (앱) 로그인 버튼 연타 | — | 진행 중에는 두 버튼 모두 누를 수 없음 | `signIn…`은 한 번만 불림 |

- **JWKS 오류 경계**: 토큰 형식·누락/비문자열/빈 `kid`는 #2, JWKS 전송·JSON 파싱·키 집합 형식 오류는 #4다. 유효한 서명 키 집합에서 해당 `kid`를 찾지 못한 경우만 #2로 분류한다. 예외 메시지 문자열로 분류하지 않는다. JWKS 어댑터는 전송·파싱 단계에서 오류를 구분해 올린다.
- **키 캐시·재조회**: `cache_keys=False`, `cache_jwk_set=True`, `lifespan=600`, `timeout=3`, `cooldown_duration=30`. 모르는 `kid`는 마지막 성공 조회로부터 30초가 지났을 때 요청당 최대 한 번 강제 재조회한다. 최초 조회·TTL 만료 조회도 cooldown을 시작한다. cooldown 중에는 추가 조회 없이 #2로 거부하고, 이후 요청에서 다시 확인한다. 강제 재조회 wrapper로 cooldown을 우회하지 않는다. 캐시는 프로세스마다 하나를 재사용하며 네트워크는 DB 트랜잭션 밖이다.
- **검증 순서(보안 가드)**: 헤더 → 설정 → JWKS → decode → role → sub → DB. 이 순서와 위 표의 예외→코드 대응은 바꾸지 않는다(골격은 구현 계획 P4).

#### C7. 다른 기능과 닿는 곳과 `TODO(연결)` 가짜 값

- `user_profiles` 생성·자동 닉네임(Q-55)은 이번 AUTH-1에 넣지 않는다. 05 §9의 AUTH-1 대조 추천과 정리안 §4대로 LOCAL-1 전 별도 계약에서 결정한다(05의 기본값을 확정하거나 바꾼 것으로 보지 않음).

| 의존 대상 역할·기능 | 필요한 함수/데이터 | 상대 머지 전 쓸 가짜 값 모양 |
| :--- | :--- | :--- |
| 모든 기능(A·B·C) → D `auth` 서버 | `from app.auth import CurrentUser, get_current_user` 후 `user: CurrentUser = Depends(get_current_user)`. 소유자 조건은 `user.id`로만 | AUTH-1-P3 머지 전: 시험에서 `app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=UUID("00000000-0000-4000-8000-00000000000a"), session_id=None)`. 사용자 B는 끝자리 `…0000b`. 머지 뒤에는 같은 override를 그대로 쓴다(진짜 JWT를 시험에서 만들 필요 없음) |
| 모든 기능(A·B·C) → D `auth` 앱 | `useAuth()`의 `status`·`userId`, 서버 호출은 `apiFetch(path, init)` | AUTH-1-P5 머지 전: `{ status: "signedIn", userId: "00000000-0000-4000-8000-00000000000a" }`, `apiFetch`는 `fetch`에 `EXPO_PUBLIC_API_URL`만 붙인 것 |
| AUTH-1-P6 → AUTH-1-P3 | `POST /api/v1/auth/session` 응답 | `{"user_id": "00000000-0000-4000-8000-00000000000a", "status": "active", "is_new": true, "created_at": "2026-11-13T09:00:00+09:00"}` |
| D 외부 설정(코드 밖, AUTH-1-P6 실로그인 확인 전) | Supabase 프로젝트(ES256 또는 RS256 서명 키 활성화·JWKS 공개 확인), Google Cloud OAuth 클라이언트(웹 유형)를 Supabase Google 제공자에 등록, Apple 제공자에 번들 ID `kr.localone.app` 등록, Supabase 리디렉트 허용 목록에 `localone://auth-callback`·`http://localhost:8081/login`(배포 웹은 같은 /login 경로) | 시험은 외부 설정 없이 돈다(가짜 JWKS). 실제 로그인 확인만 이 설정이 필요하다 |

### 구현 계획

> 누가 어느 파일을 어느 브랜치에서 고치나(태스크). 여기만 고치면 약속은 바뀌지 않는다. 고치는 커밋은 머리말 `plan:`.

#### P1. 확인한 기존 코드 전제 (`file:line` 근거, 코드 레포 `main` `1353eb4`)

| 참조 대상 | 실제 경로와 줄 (`file:line`) | 재사용할 심볼·시그니처·역할 |
| :--- | :--- | :--- |
| 에러 응답 헬퍼 | `server/app/common.py:L11-L16` | `error_response(status_code, code, message, detail="") -> JSONResponse` |
| KST 현재 시각 | `server/app/common.py:L19-L25` | `now_kst(now=None) -> datetime` — 응답의 시각을 서울 시간대로 바꿀 때 쓴다 |
| 앱 만들기 | `server/app/main.py:L27-L85` | `create_app(settings: Settings \| None = None) -> FastAPI`. 파트 1에서 인자 `jwks_client`를 더한다(P4) |
| DB 엔진 | `server/app/main.py:L31-L35`, `L45` | 동기 엔진 `app.state.engine`. psycopg 비동기는 Windows에서 안 돼 **동기 엔진 + `asyncio.to_thread`**로 쓴다(`L56-L69` `_ping`·`ready` 방식) |
| 오류 처리기 | `server/app/main.py:L71-L83` | 404·405·422·500을 공통 형식으로 바꾼다. 파트 1에서 `ApiError` 처리기를 하나 더한다 |
| 설정 | `server/app/settings.py:L18-L36` | `Settings(app_env, database_url)`. `APP_ENV=test`는 로컬 DB만 허용(`L33-L35`). 파트 1에서 `supabase_url`을 더한다 |
| 시험 DB | `docker-compose.yml`(postgres:17, 포트 5433), `server/tests/test_ready.py:L13-L15` | `DATABASE_URL` 환경 변수, 없으면 `postgresql+psycopg://localone:localone@localhost:5433/localone_test` |
| 시험 클라이언트 | `server/tests/test_ready.py:L40` 이하 | `TestClient(create_app(Settings(...)))` 방식 |
| 앱 라우팅 | `mobile/app/_layout.tsx:L1-L5` | expo-router `Stack`. AUTH-1-P5에서 인증 상태 공급자로 감싼다 |
| 앱 API 주소 | `mobile/app/index.tsx:L6` | `process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000"` |
| 앱 딥링크 이름 | `mobile/app.json` `expo.scheme` = `"localone"` | 로그인 복귀 주소 `localone://auth-callback` |
| 웹 출력 | `mobile/app.json` `expo.web.output` = `"single"` | 서버 렌더링 없음 → 저장소 어댑터에 SSR 분기를 두지 않는다 |

#### P2. 파트 분할과 담당 파일

> **2026-11-13 D 추가 승인(C-59):** 기존 2파트를 아래 6파트로 대체했다. 태스크 ID는 미착수 상태에서 재정의하며 옛 AUTH-1-P1(전체 서버)·P2(전체 앱)는 더 이상 실행 단위가 아니다. 각 파트는 7파일 이하·핵심 로직 5파일 이하이며 빈 골격만 만드는 파트는 없다. 표의 줄 수는 수동 작성 부분의 추정이다. P1·P4의 생성 잠금 파일을 포함한 전체 변경량은 아직 측정하지 않았으므로, 의존성 해석 후 제품 구현 전에 전체 diff가 700줄 이내인지 확인하고 넘으면 계획부터 다시 나눈다. 상한 예외를 승인한 것은 아니다. 실제 diff가 상한을 넘으면 구현 전에 이 계획부터 다시 나눈다. 이번 작업은 문서·시안이며 구현 미착수다.

| 태스크 | 브랜치 | 수정/생성 허용 파일(전수) | 검증할 행동·예상 변경량 |
| --- | --- | --- | --- |
| `AUTH-1-P1` JWT 검증·공통 오류 | `feat/auth-1-part1` | `server/app/auth.py`, `server/app/common.py`, `server/app/main.py`, `server/app/settings.py`, `server/tests/test_auth_jwt.py`, `server/pyproject.toml`, `server/uv.lock` | A1·A3 / C6 #1~#4 / JWT·kid·JWKS 오류·회전·cooldown·캐시 시험. 실제 보호 API 대신 시험 전용 보호 경로로 verify_access_token을 실행하며 DB 호출 0회 / 7파일, 450~650줄(추정) |
| `AUTH-1-P2` users 저장·격리 DB 마이그레이션 | `feat/auth-1-part2` | `server/app/db.py`, `server/alembic.ini`, `server/migrations/env.py`, `server/migrations/script.py.mako`, `server/migrations/versions/0001_users.py`, `server/tests/conftest.py`, `server/tests/test_auth_storage.py` | A5 / C5 전 컬럼·제약·RLS / run_db의 commit·rollback·연결 실패 / migration round-trip. 로컬 격리 DB에 실제 SQL을 실행해 쓰기·실패 후 무변경 검증 / 7파일, 300~500줄(추정) |
| `AUTH-1-P3` 로그인 등록·내 사용자 API 연결 | `feat/auth-1-part3` | `server/app/auth.py`, `server/app/main.py`, `server/tests/test_auth_session.py`, `.env.example`, `.github/workflows/ci.yml` | A1·A3·A5·A6 / C2 두 경로·C3 응답·C6 #1~#8 / 중복·동시 등록·다른 사용자 id 무시·탈퇴 거부·DB 실패 후 무변경 / 5파일, 300~550줄(추정) |
| `AUTH-1-P4` 앱 OAuth·저장소·플랫폼 어댑터 | `feat/auth-1-part4` | `mobile/src/auth/supabase.ts`, `mobile/src/auth/platform.ts`, `mobile/src/auth/__tests__/platform.test.ts`, `mobile/jest.config.js`, `mobile/.env.example`, `mobile/package.json`, `mobile/package-lock.json` | A2·A7·A8 / C4 분기 / 제공자 취소·오류·nonce 전달·저장소·AppState 구독 정리 시험. Supabase 클라이언트는 한 인스턴스, 테스트는 외부 제공자 미호출 / 7파일, 400~650줄(추정) |
| `AUTH-1-P5` 앱 인증 상태·서버 통신 연결 | `feat/auth-1-part5` | `mobile/src/auth/AuthProvider.tsx`, `mobile/src/auth/apiFetch.ts`, `mobile/src/auth/__tests__/AuthProvider.test.tsx`, `mobile/src/auth/__tests__/apiFetch.test.ts`, `mobile/app/_layout.tsx` | C2 useAuth·apiFetch / C6 #3·#5·#9~#11 / 복구 실패·전체 1회 재전송·등록 실패 시 signedIn 금지 / 구독 해제·오래된 완료 무시 / 5파일, 350~600줄(추정) |
| `AUTH-1-P6` 선택한 로그인 화면·실제 여정 확인 | `feat/auth-1-part6` | `mobile/app/login.tsx`, `mobile/app/index.tsx`, `mobile/app.json`, `mobile/src/auth/__tests__/login.test.tsx` | A2·A7·A8·A9 / C6 #9~#12 / C4 웹·Android·iOS 각 확인. 로그인 시작→제공자→등록 성공→스모크 로그인함, 실패·취소는 거짓 성공 없음 / 4파일, 250~450줄(추정) |

- main.py는 `# ── [auth-D] ──` 블록을 사용한다. 각 파트 브랜치는 이전 파트가 아닌 최신 origin/main에서 만든다. 서버 회귀 명령 전에는 루트에서 `docker compose up -d --wait db`로 기존 ready 시험용 로컬 격리 DB를 띄운다. Windows의 APP_ENV 표기는 `$env:APP_ENV="test"` 후 명령을 실행한다. 예측 줄 수는 구현 전 추정이며 통과 증거가 아니다.

##### 파트 머리말 — AUTH-1-P1

| 칸 | 값 |
| --- | --- |
| 1. 태스크 ID | `AUTH-1-P1` |
| 2. 담당 역할 | D |
| 3. 기준선 버전 | B1(C-59 갱신) |
| 4. 계약서 커밋 | `adc60726d7a9eb1f90964c85d73df1d7ea65d615` (C-60 확정 본문 커밋) |
| 5. 선행 태스크 | 없음(최신 main·B1 계약 SHA 확인) |
| 6. 수정 허용 파일 | 위 AUTH-1-P1 행의 7개 실제 경로만 |
| 7. 금지된 결정·수정 경계 | auth.py는 CurrentUser·JWT 검증·JWKS 어댑터만, common.py는 ApiError 추가, main.py는 주입·ApiError 처리기만, settings.py는 supabase_url만. Alembic·PyJWT 의존성 2개 추가. DB·제품 auth 경로 등록 금지 |
| 8. 완료 조건 | A1·A3 / C6 #1~#4 / JWT·kid·JWKS 오류·회전·cooldown·캐시 시험. 실제 보호 API 대신 시험 전용 보호 경로로 verify_access_token을 실행하며 DB 호출 0회 및 P5의 해당 태스크 시험 통과 |
| 9. 검증 명령 | server에서 python -m uv sync --locked → APP_ENV=test python -m uv run pytest -W error tests/test_auth_jwt.py tests/test_ready.py tests/test_cors.py |
| 10. 보고 형식 | prompts/3_구현.md 5단계와 코드 레포 PR 템플릿. 주니어 이해 확인은 N/A(D 담당), 실행 명령·대상 revision·실제 출력·미실행 플랫폼 별도 기록 |

##### 파트 머리말 — AUTH-1-P2

| 칸 | 값 |
| --- | --- |
| 1. 태스크 ID | `AUTH-1-P2` |
| 2. 담당 역할 | D |
| 3. 기준선 버전 | B1(C-59 갱신) |
| 4. 계약서 커밋 | `adc60726d7a9eb1f90964c85d73df1d7ea65d615` (C-60 확정 본문 커밋) |
| 5. 선행 태스크 | AUTH-1-P1 머지 |
| 6. 수정 허용 파일 | 위 AUTH-1-P2 행의 7개 실제 경로만 |
| 7. 금지된 결정·수정 경계 | 동기 SQLAlchemy·스레드 경계와 users 테이블만. auth.users FK·user_profiles·제품 엔드포인트 없음. 시험 세션 migration·시험별 users 정리는 conftest.py에 한 번 |
| 8. 완료 조건 | A5 / C5 전 컬럼·제약·RLS / run_db의 commit·rollback·연결 실패 / migration round-trip. 로컬 격리 DB에 실제 SQL을 실행해 쓰기·실패 후 무변경 검증 및 P5의 해당 태스크 시험 통과 |
| 9. 검증 명령 | 루트에서 docker compose up -d --wait db → server에서 APP_ENV=test python -m uv run alembic upgrade head → APP_ENV=test python -m uv run pytest -W error tests/test_auth_storage.py tests/test_ready.py tests/test_cors.py |
| 10. 보고 형식 | prompts/3_구현.md 5단계와 코드 레포 PR 템플릿. 주니어 이해 확인은 N/A(D 담당), 실행 명령·대상 revision·실제 출력·미실행 플랫폼 별도 기록 |

##### 파트 머리말 — AUTH-1-P3

| 칸 | 값 |
| --- | --- |
| 1. 태스크 ID | `AUTH-1-P3` |
| 2. 담당 역할 | D |
| 3. 기준선 버전 | B1(C-59 갱신) |
| 4. 계약서 커밋 | `adc60726d7a9eb1f90964c85d73df1d7ea65d615` (C-60 확정 본문 커밋) |
| 5. 선행 태스크 | AUTH-1-P2 머지 |
| 6. 수정 허용 파일 | 위 AUTH-1-P3 행의 5개 실제 경로만 |
| 7. 금지된 결정·수정 경계 | auth.py에 get_current_user·라우터만, main.py auth 블록에 라우터 등록만. .env.example SUPABASE_URL·CI migration 단계 추가. P1 JWT 검증 재작성·다른 API·세션 발급 금지 |
| 8. 완료 조건 | A1·A3·A5·A6 / C2 두 경로·C3 응답·C6 #1~#8 / 중복·동시 등록·다른 사용자 id 무시·탈퇴 거부·DB 실패 후 무변경 및 P5의 해당 태스크 시험 통과 |
| 9. 검증 명령 | 격리 DB 실행 후 server에서 APP_ENV=test python -m uv run alembic upgrade head → APP_ENV=test python -m uv run pytest -W error |
| 10. 보고 형식 | prompts/3_구현.md 5단계와 코드 레포 PR 템플릿. 주니어 이해 확인은 N/A(D 담당), 실행 명령·대상 revision·실제 출력·미실행 플랫폼 별도 기록 |

##### 파트 머리말 — AUTH-1-P4

| 칸 | 값 |
| --- | --- |
| 1. 태스크 ID | `AUTH-1-P4` |
| 2. 담당 역할 | D |
| 3. 기준선 버전 | B1(C-59 갱신) |
| 4. 계약서 커밋 | `adc60726d7a9eb1f90964c85d73df1d7ea65d615` (C-60 확정 본문 커밋) |
| 5. 선행 태스크 | B1(C-59) 계약 SHA 확정 후 독립 진행 가능; 서버 구현 미머지이면 C7 가짜 값만 사용 |
| 6. 수정 허용 파일 | 위 AUTH-1-P4 행의 7개 실제 경로만 |
| 7. 금지된 결정·수정 경계 | P3 승인 앱 라이브러리와 jest만 도입. Platform.OS는 platform.ts 한 곳. 로그인 화면·AuthProvider·app.json 설정 변경은 아직 하지 않음 |
| 8. 완료 조건 | A2·A7·A8 / C4 분기 / 제공자 취소·오류·nonce 전달·저장소·AppState 구독 정리 시험. Supabase 클라이언트는 한 인스턴스, 테스트는 외부 제공자 미호출 및 P5의 해당 태스크 시험 통과 |
| 9. 검증 명령 | mobile에서 npm ci → npx tsc --noEmit → npx jest --runInBand src/auth/__tests__/platform.test.ts → npx expo export --platform web |
| 10. 보고 형식 | prompts/3_구현.md 5단계와 코드 레포 PR 템플릿. 주니어 이해 확인은 N/A(D 담당), 실행 명령·대상 revision·실제 출력·미실행 플랫폼 별도 기록 |

##### 파트 머리말 — AUTH-1-P5

| 칸 | 값 |
| --- | --- |
| 1. 태스크 ID | `AUTH-1-P5` |
| 2. 담당 역할 | D |
| 3. 기준선 버전 | B1(C-59 갱신) |
| 4. 계약서 커밋 | `adc60726d7a9eb1f90964c85d73df1d7ea65d615` (C-60 확정 본문 커밋) |
| 5. 선행 태스크 | AUTH-1-P4 머지. AUTH-1-P3 미머지이면 C7 응답으로 진행·TODO(연결), 실제 연결 완료 판정은 P3 뒤 |
| 6. 수정 허용 파일 | 위 AUTH-1-P5 행의 5개 실제 경로만 |
| 7. 금지된 결정·수정 경계 | _layout.tsx는 공급자로 감싸기만. 사용자 전환·로그아웃 기능은 AUTH-2에 남기되 unmount·요청 세대가 지난 완료를 무시하는 내부 수명 가드는 필수. 제품 화면 배치·하단 탭 없음 |
| 8. 완료 조건 | C2 useAuth·apiFetch / C6 #3·#5·#9~#11 / 복구 실패·전체 1회 재전송·등록 실패 시 signedIn 금지 / 구독 해제·오래된 완료 무시 및 P5의 해당 태스크 시험 통과 |
| 9. 검증 명령 | mobile에서 npx tsc --noEmit → npx jest --runInBand src/auth/__tests__/AuthProvider.test.tsx src/auth/__tests__/apiFetch.test.ts → npx expo export --platform web |
| 10. 보고 형식 | prompts/3_구현.md 5단계와 코드 레포 PR 템플릿. 주니어 이해 확인은 N/A(D 담당), 실행 명령·대상 revision·실제 출력·미실행 플랫폼 별도 기록 |

##### 파트 머리말 — AUTH-1-P6

| 칸 | 값 |
| --- | --- |
| 1. 태스크 ID | `AUTH-1-P6` |
| 2. 담당 역할 | D |
| 3. 기준선 버전 | B1(C-59 갱신) |
| 4. 계약서 커밋 | `adc60726d7a9eb1f90964c85d73df1d7ea65d615` (C-60 확정 본문 커밋) |
| 5. 선행 태스크 | AUTH-1-P3·P5 머지 + C7 외부 설정 (A9 확정 완료) |
| 6. 수정 허용 파일 | 위 AUTH-1-P6 행의 4개 실제 경로만 |
| 7. 금지된 결정·수정 경계 | login.tsx는 채택 A9 배치만, index.tsx 로그인 상태 한 줄·로그인 버튼만, app.json plugins·ios.usesAppleSignIn만. 웹 복귀 주소는 기존 /login 경로로 고정·detectSessionInUrl로 PKCE code 처리, 네이티브는 localone://auth-callback 브라우저 세션 복귀. 새 탭·프로필·로그아웃 없음 |
| 8. 완료 조건 | A2·A7·A8·A9 / C6 #9~#12 / C4 웹·Android·iOS 각 확인. 로그인 시작→제공자→등록 성공→스모크 로그인함, 실패·취소는 거짓 성공 없음 및 P5의 해당 태스크 시험 통과 |
| 9. 검증 명령 | mobile에서 npx tsc --noEmit → npx jest --runInBand → npx expo export --platform web; 웹·Android 실로그인 및 D의 iOS 확인을 별도 기록 |
| 10. 보고 형식 | prompts/3_구현.md 5단계와 코드 레포 PR 템플릿. 주니어 이해 확인은 N/A(D 담당), 실행 명령·대상 revision·실제 출력·미실행 플랫폼 별도 기록 |

- **선행 미머지 범위**: AUTH-1-P4는 외부 제공자 가짜로 OAuth 어댑터 시험까지, P5는 P4가 머지된 뒤 C7 서버 가짜 응답으로 상태·재시도 시험까지 진행할 수 있다. P3 전의 연결을 실로그인 성공으로 보고하지 않는다.

#### P3. 새 라이브러리 (이 목록 밖은 추가하지 않는다)

| 쪽 | 패키지 | 용도 | 설정 / 웹에서 |
| :--- | :--- | :--- | :--- |
| 서버 | `alembic` | 마이그레이션(Q-28) | — |
| 서버 | `pyjwt[crypto]>=2.15.1,<3` | JWT 검증·JWKS(`PyJWKClient`). 시험의 키 만들기는 함께 들어오는 `cryptography`로 | — |
| 앱 | `@supabase/supabase-js` | Supabase Auth 클라이언트 | 세 플랫폼 공통 |
| 앱 | `@react-native-async-storage/async-storage` | 세션 저장(A8) | 웹은 쓰지 않음(`localStorage`) |
| 앱 | `react-native-url-polyfill` | supabase-js가 쓰는 URL API(Supabase Expo 문서) | 웹은 불필요하지만 넣어도 동작 같음 |
| 앱 | `expo-web-browser`, `expo-auth-session` | Google 로그인 창·복귀 주소 | 웹은 전체 페이지 이동(C4) |
| 앱 | `expo-apple-authentication` | Apple 로그인 | config plugin `"expo-apple-authentication"` + `ios.usesAppleSignIn: true`. 웹·Android 미사용 |
| 앱 | `expo-crypto` | Apple nonce의 SHA-256 | 세 플랫폼 공통 |
| 앱(개발) | `jest-expo`, `@testing-library/react-native` | 화면 자동 테스트 첫 도입(Q-27) | — |

- 버전은 `npx expo install`·`uv add`가 고른 값을 쓰고 PR 본문에 적는다.

#### P4. 핵심 흐름 골격 (구조 변경 금지)

```python
# [보존 골격] 헤더 → JWKS 키(외부 I/O, DB 밖) → 클레임 검사 → (필요할 때만) DB
ALLOWED_ALGS = ["ES256", "RS256"]

async def verify_access_token(request: Request) -> CurrentUser:
    s = request.app.state.settings
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError(401, "AUTH_REQUIRED", "로그인이 필요해요.")
    token = header.removeprefix("Bearer ")
    if not s.supabase_url:
        raise ApiError(503, "AUTH_UNAVAILABLE", MSG_UNAVAILABLE)
    try:   # JWKS 조회는 네트워크라 스레드에서, DB 트랜잭션 밖에서
        key = await asyncio.to_thread(resolve_signing_key, request.app.state.jwks_client, token)
    except JwksUnavailableError:                  # 전송·JSON·키 집합 오류(#4)
        raise ApiError(503, "AUTH_UNAVAILABLE", MSG_UNAVAILABLE)
    except (UnknownSigningKeyError, jwt.InvalidTokenError):  # #2
        raise ApiError(401, "AUTH_INVALID", MSG_INVALID)
    try:
        claims = jwt.decode(token, key.key, algorithms=ALLOWED_ALGS, audience="authenticated",
                            issuer=f"{s.supabase_url}/auth/v1", leeway=10,
                            options={"require": ["exp", "iss", "aud", "sub"]})
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "AUTH_EXPIRED", MSG_EXPIRED)
    except jwt.PyJWTError:
        raise ApiError(401, "AUTH_INVALID", MSG_INVALID)
    if claims.get("role") != "authenticated":
        raise ApiError(401, "AUTH_INVALID", MSG_INVALID)
    user_id = parse_uuid_or_raise_invalid(claims["sub"])
    return CurrentUser(id=user_id, session_id=claims.get("session_id"))

async def get_current_user(request: Request) -> CurrentUser:
    user = await verify_access_token(request)
    row = await run_db(request.app.state.engine, lambda c: select_user(c, user.id))
    if row is None:
        raise ApiError(401, "AUTH_NOT_REGISTERED", "다시 로그인해 주세요.")
    if row.status != "active":
        raise ApiError(403, "ACCOUNT_WITHDRAWN", "탈퇴한 계정이에요.")
    return user

@router.post("/api/v1/auth/session")
async def create_session(request: Request, user: CurrentUser = Depends(verify_access_token)):
    def tx(c):   # INSERT … ON CONFLICT (id) DO NOTHING RETURNING id → 없으면 기존 행 SELECT
        inserted = insert_user_if_absent(c, user.id)
        return select_user(c, user.id), inserted
    row, is_new = await run_db(request.app.state.engine, tx)
    if row.status != "active":
        raise ApiError(403, "ACCOUNT_WITHDRAWN", "탈퇴한 계정이에요.")
    return {"user_id": str(row.id), "status": row.status, "is_new": is_new,
            "created_at": now_kst(row.created_at).isoformat(timespec="seconds")}
```

- **2026-11-13 공식 재확인**: [Supabase JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys)의 공개키 경로는 A3와 같고 비대칭 알고리즘은 ES256·RS256이다. 프로젝트는 이 중 하나를 활성화해야 한다(HS256 프로젝트는 이 계약으로 로그인 불가). [PyJWT 2.15.1 소스](https://github.com/jpadilla/pyjwt/blob/2.15.1/jwt/jwks_client.py)의 `get_signing_key`는 C6의 30초 cooldown 뒤 모르는 `kid`를 한 번 재조회한다. `cache_keys=True`는 키를 TTL 없이 보관하므로 쓰지 않는다. **실행 검증은 아직 안 했으며**, AUTH-1-P1 구현 시 잠금 버전으로 구현 계획 P5의 JWT 시험을 검증한다. 다른 버전을 선택하면 C6 동작과의 일치를 먼저 확인한다.
- 위 이름 중 `select_user`·`insert_user_if_absent`·`parse_uuid_or_raise_invalid`·`resolve_signing_key`·`JwksUnavailableError`·`UnknownSigningKeyError`·`MSG_*`는 `auth.py` 안의 이름이고 모양은 구현이 정한다. 순서와 예외→코드 대응은 계약 C6에 있다.

AUTH 안에서만 쓰는 함수(바꿔도 다른 기능이 모른다):

- `def build_jwks_client(settings: Settings) -> JwksClient` — `jwt.PyJWKClient(<SUPABASE_URL>/auth/v1/.well-known/jwks.json, cache_keys=False, cache_jwk_set=True, lifespan=600, timeout=3, cooldown_duration=30)`. `JwksClient`는 `get_signing_key_from_jwt(token: str) -> PyJWK`를 가진 Protocol이고, 시험은 같은 Protocol의 가짜를 넣는다.
- `create_app(settings: Settings | None = None, jwks_client: JwksClient | None = None) -> FastAPI` — 없으면 `build_jwks_client(settings)`. 결과를 `app.state.jwks_client`에 둔다.
- `mobile/src/auth/platform.ts`: `isAppleSignInAvailable(): Promise<boolean>`, `startGoogleSignIn(): Promise<SignInResult>`, `authStorage`(Supabase `auth.storage`에 넘길 저장소), `watchAppForeground(supabase): () => void`. **`Platform.OS`는 이 파일에서만 쓴다**(C4).

#### P5. 필수 테스트

| 파트 | 테스트 이름 | 준비 (Given) | 실행 (When) | 기대 단언 (Then) | 잡아야 할 버그 (가드를 빼면 실패할 것) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| AUTH-1-P3 | `test_session_creates_user_once` | 빈 `users`, 사용자 A의 유효 토큰 | `POST /auth/session` 두 번 | 첫 응답 `is_new: true`, 둘째 `false`, 두 `created_at` 같음, 행 1개 | `ON CONFLICT` 누락(두 번째가 500 또는 행 2개) |
| AUTH-1-P3 | `test_session_concurrent_same_user_one_row` | 빈 `users`, A 토큰 | 스레드 두 개로 동시에 `POST /auth/session` | 둘 다 `200`, 행 1개, `is_new: true`는 정확히 하나 | 먼저 SELECT 후 INSERT하는 경합 |
| AUTH-1-P3 | `test_session_ignores_body_user_id` | 빈 `users`, A 토큰 | 본문 `{"user_id": "<B의 id>"}`로 `POST` | 응답 `user_id`가 A, B의 행 없음 | 본문 id 사용(불변 조건 4) |
| AUTH-1-P1 | `test_missing_header_is_auth_required` | DB 미사용 | 헤더 없이 시험 전용 보호 경로, `Basic xxx` 헤더로도 | `401 AUTH_REQUIRED`, 오류 키 `code·message·detail`, DB 호출 0회 | 헤더 검사 누락 |
| AUTH-1-P1 | `test_expired_token_is_auth_expired` | `exp` = 지금 − 60초 | 시험 전용 보호 경로 | `401 AUTH_EXPIRED`, DB 호출 0회 | 만료 검사 누락·`leeway` 과대 |
| AUTH-1-P1 | `test_wrong_issuer_rejected` | `iss` = 다른 프로젝트 주소 | 시험 전용 보호 경로 | `401 AUTH_INVALID`, DB 호출 0회 | `issuer` 인자 누락 |
| AUTH-1-P1 | `test_wrong_audience_rejected` | `aud` = `"anon"` | 시험 전용 보호 경로 | `401 AUTH_INVALID`, DB 호출 0회 | `audience` 누락 |
| AUTH-1-P1 | `test_anon_role_rejected` | `role` = `"anon"`, 나머지 유효 | 시험 전용 보호 경로 | `401 AUTH_INVALID`, DB 호출 0회 | `role` 검사 누락(publishable 키 JWT로 가입) |
| AUTH-1-P1 | `test_hs256_and_none_rejected` | 같은 클레임을 `HS256`(아무 비밀값)·`alg: none`으로 서명 | 시험 전용 보호 경로 | 둘 다 `401 AUTH_INVALID`, DB 호출 0회 | `algorithms` 목록 누락(알고리즘 바꿔치기) |
| AUTH-1-P1 | `test_bad_signature_rejected` | 다른 EC 키로 서명, `kid`는 JWKS에 있는 값 | 시험 전용 보호 경로 | `401 AUTH_INVALID`, DB 호출 0회 | 서명 검증 끄기 |
| AUTH-1-P1 | `test_unknown_kid_refetches_once` | 실제 `PyJWKClient` + HTTP 응답만 가짜. 키 1로 캐시 예열, 단조 시계를 30초 이상 진행시킨 뒤 키 2 공개 | 키 2 토큰으로 시험 전용 보호 경로 | `200`, 예열 1회 + 강제 재조회 1회 = HTTP 총 2회 | 키 회전을 못 따라감 / 재조회 wrapper 중복 |
| AUTH-1-P1 | `test_unknown_kid_cooldown` | 위 클라이언트, 키 1 예열 직후 | 모르는 kid로 여러 번 시험 전용 보호 경로, 30초 뒤 키 2 공개 후 재요청 | cooldown 중 `401 AUTH_INVALID`·HTTP 추가 0회·DB 호출 0회, 이후 `200`·추가 1회 | 모르는 kid마다 외부 조회 / cooldown 영구 고착 |
| AUTH-1-P1 | `test_revoked_key_leaves_cache_after_ttl` | 실제 클라이언트로 키 1 예열, 이후 JWKS에서 키 1 제거 | 단조 시계 600초 후 키 1 토큰 요청 | `401 AUTH_INVALID`, 키 1로 성공하지 않음 | 무기한 개별 키 캐시 |
| AUTH-1-P1 | `test_jwks_unavailable_is_503` | 가짜 JWKS가 `PyJWKClientConnectionError`를 던짐 | 시험 전용 보호 경로 | `503 AUTH_UNAVAILABLE`, DB 호출 0회 | 연결 실패를 성공이나 `401`로 삼킴 |
| AUTH-1-P1 | `test_malformed_jwks_is_503` | HTTP는 성공하되 깨진 JSON·JSON 배열·keys 누락·빈/손상 키 집합을 각각 응답 | 실제 클라이언트·어댑터로 시험 전용 보호 경로 | 전부 `503 AUTH_UNAVAILABLE`, DB 호출 0회 | JWKS 장애를 401·500으로 오분류 |
| AUTH-1-P1 | `test_invalid_claims_and_kid_rejected` | 필수 클레임 누락·잘못된 UUID sub·role 누락·kid 누락/비문자열/빈 값 각각 | 시험 전용 보호 경로 | `401 AUTH_INVALID`, DB 호출 0회; kid 형식 오류는 HTTP 조회 0회 | 누락 클레임 허용·토큰 오류를 503으로 오분류 |
| AUTH-1-P3 | `test_auth_db_failure_is_503` | 유효 JWT, DB 연결 실패 | `POST /auth/session`·`GET /me` | `503 DB_UNAVAILABLE`, 행 무변경 | DB 실패를 성공·401로 삼킴 |
| AUTH-1-P1 | `test_empty_supabase_url_is_503` | `Settings(supabase_url="")` | 시험 전용 보호 경로 | `503 AUTH_UNAVAILABLE` | 빈 설정으로 `iss` 검사가 느슨해짐 |
| AUTH-1-P3 | `test_me_returns_own_user` | A·B 행, A 토큰 | `GET /me` | `200`, `user_id` = A | 토큰이 아닌 다른 경로로 사용자 고름 |
| AUTH-1-P3 | `test_me_not_registered` | 빈 `users`, A 토큰 | `GET /me` | `401 AUTH_NOT_REGISTERED`, 행 0개 | `get_current_user`가 행을 몰래 만듦 |
| AUTH-1-P3 | `test_withdrawn_user_forbidden` | A 행 `status='withdrawn'` | `POST /auth/session`, `GET /me` | 둘 다 `403 ACCOUNT_WITHDRAWN`, A 행 `status`·`created_at` 그대로 | 탈퇴 계정 되살리기(`ON CONFLICT DO UPDATE`) |
| AUTH-1-P2 | `test_users_status_check` | — | SQL로 `status='x'` 넣기 | `IntegrityError`, 행 0개 | CHECK 누락 |
| AUTH-1-P2 | `test_users_rls_enabled` | 마이그레이션 적용 | `SELECT relrowsecurity FROM pg_class WHERE relname='users'` | `true`, `pg_policies`에 `users` 정책 0개 | RLS 줄 누락 |
| AUTH-1-P2 | `test_migration_round_trip` | 빈 DB | `alembic upgrade head` → `downgrade base` → `upgrade head` | 오류 없음, 마지막에 `users` 있음 | `downgrade` 누락 |
| AUTH-1-P6 | `login_button_double_tap_calls_once` | `signInWithGoogle`가 끝나지 않는 가짜 | Google 버튼 두 번 누름 | 가짜가 1번 불림, 진행 표시가 보임 | 진행 중 버튼 막기 누락(예외 #12) |
| AUTH-1-P6 | `login_cancel_shows_no_error` | 가짜가 `{ok:false, reason:"cancelled"}` | 버튼 누름 | 오류 문구 없음, 버튼 다시 누를 수 있음 | 취소를 오류로 표시(예외 #9) |
| AUTH-1-P6 | `login_failure_shows_copy` | 가짜가 `failed` / `network` | 버튼 누름 | 각각 예외 #10·#11 문구 그대로 | 개발자 오류 원문 노출 |
| AUTH-1-P6 | `apple_button_hidden_when_unavailable` | `isAppleSignInAvailable`이 `false`인 가짜 | 로그인 화면 그림 | Apple 버튼 없음, Google 버튼 있음 | 플랫폼 분기 누락(A2) |
| AUTH-1-P5 | `apiFetch_retries_once_on_expired` | 첫 응답 `401 AUTH_EXPIRED`, 둘째 `200` / 둘 다 `401 AUTH_EXPIRED` | `apiFetch` | 앞은 `200`·갱신 1번, 뒤는 `401`·요청 정확히 2번 | 무한 재시도 / 재시도 없음 |
| AUTH-1-P5 | `apiFetch_recovery_failure_and_changed_code` | 갱신/등록 실패 또는 재전송이 다른 401 코드를 반환 | `apiFetch` | 복구 실패 응답 반환·원 요청 재전송 0회, 코드 변경 시에도 총 재전송 1회 이하, 자기 재귀 없음 | 오류별 재시도 누적으로 무한 복구 |
| AUTH-1-P5 | `apiFetch_registers_once_on_not_registered` | 첫 응답 `401 AUTH_NOT_REGISTERED`, `POST /auth/session` `200`, 다시 `200` | `apiFetch` | `200`, `/auth/session` 1번 | #5 경로 누락 |
| AUTH-1-P2 | `test_run_db_commit_rollback` | 격리 DB·동기 함수·쓰기 후 ApiError 함수 | run_db 호출 | 성공 commit·실패 rollback·연결 실패 503 / 이벤트 루프 밖 실행 | 트랜잭션/스레드 경계 누락 |
| AUTH-1-P3 | `test_invalid_token_does_not_create_user` | C6 #1~#4별 토큰·가짜 HTTP 장애·빈 users | 실제 POST /auth/session·GET /me | 계약 HTTP/code, 행 0개, get_current_user의 쓰기 없음 | 단위 검증을 실제 경로에 연결하지 않음 |
| AUTH-1-P4 | `oauth_adapter_lifecycle` | 실제 어댑터+SDK/저장소/AppState 가짜 | Google PKCE code·취소·Apple nonce·저장/재시작·foreground/cleanup | 계약 인자·결과·저장소 재사용·구독 정리·Apple 미지원 시 false | 잘못된 nonce·취소 오분류·중복 구독 |
| AUTH-1-P5 | `provider_registration_gate` | Supabase 세션 있음·등록 200/503/403 각각 | 초기 복원·로그인 완료 | 200만 signedIn/userId; 실패는 signedIn 아님, unmount/세대 지난 완료 무시 | Supabase만 성공하면 로그인함 표시·늦은 완료 |

- JWKS 재조회·cooldown·키 폐기·깨진 응답 시험은 `JwksClient` 결과를 미리 정하는 가짜로 대신하지 않는다. 잠금 버전의 실제 `PyJWKClient`와 어댑터를 실행하고 HTTP·시계만 격리한다(대기 sleep 없음).
- 시험용 JWT는 `cryptography`로 만든 EC P-256 키로 서명하고, `conftest.py`의 가짜 `JwksClient`가 그 공개키를 돌려준다. 실제 Supabase·Google·Apple은 부르지 않는다(`3_구현.md` 1단계 4번).
- AUTH-1-P1 JWT 시험은 DB를 쓰지 않는다. P2 이후 `users`는 시험마다 `TRUNCATE`한다. 마이그레이션은 시험 세션 시작 때 한 번 `upgrade head`.

### 템플릿을 처음 써 보며 막힌 칸 (T1~T12)

코드 레포 `개발산출물/결과/AUTH-1_계약서_템플릿_점검.md`로 옮겼다(D용 기록, 구현 Claude는 읽지 않아도 됨).
