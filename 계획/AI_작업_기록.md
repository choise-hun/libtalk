# AI 작업 기록 및 세션 인계 공유 문서 (Multi-LLM Shared Work Log)

> **문서 성격**: 이 문서는 여러 세션과 여러 LLM 모델(구현 AI ↔ Phase별 적대적 리뷰·테스트 AI)이 동네한권(`choise-hun/libtalk`)의 구현 상태, 검증 결과, 다음 작업 인계 사항을 끊김 없이 공유하는 **단일 작업 상태판(Shared State Board)**이다.
> **참조 문서**:
> - 구현 및 역이식 규칙: [CLAUDE.md](../CLAUDE.md)
> - 결함 방지 및 적대적 리뷰 규칙: [하네스_엔지니어링_규칙.md](하네스_엔지니어링_규칙.md)
> - 전체 커밋 로드맵: [상용_서비스_계획.md](상용_서비스_계획.md)

---

## 1. 현재 진행 위치 요약

- **현재 Phase**: **Phase 1 — DB 스키마·시드 기반 및 인증(`AUTH-1~3`) 1~5번 전 구간 구현 및 실행 검증 완료**
- **직전 완료 Step**: Phase 1 — **5번 `AUTH-2-3`** (`d467c9d`, 내 설정 조회/변경, 로그아웃 정화 및 회원 탈퇴 `DELETE /api/v1/me`)
- **현재 관문**: **Phase 1 코드 적대적 리뷰 통과(2026-11-15, §5)** — 수정 커밋 `d145fe5`~`f70e77f`, 남은 기한부 결함 `DEF-019`(LIB-1 전)
- **다음 착수 Phase / Step (리뷰 통과 후)**: **Phase 2 — 6번 `LIB-0` 공통 조회 엔진**부터(`LIB-0` → `LIB-1` → `LIB-2` → `LIB-3`, [계획 §3](상용_서비스_계획.md))
- **문서 정합 리뷰(2026-11-15)**: 계획·02·05·06·규칙 문서를 적대적 리뷰해 고쳤다(§5 표, `DEF-007`~`DEF-012`, 커밋 `d97bc8f`)
- **Phase 1 코드 리뷰(2026-11-15)**: `DEF-008`·`DEF-013`~`DEF-018` 수정, `DEF-019`·`DEF-020` 등록(§5, 하네스 §6)

---

## 2. Phase 1 ~ Phase 7 전체 커밋 진행 현황표

### Phase 1. DB 스키마·시드 기반 및 인증(`AUTH-1~3`) 완결
| 순서 | Step ID | 커밋 메시지 / 범위 | 상태 | 커밋 SHA | 검증 결과 |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 선행 | `INIT` | `SET-0~SET-5` 서버·앱 뼈대, CORS, 번들 ID, CI | **완료** | `1353eb4` 이전 | `test_ready.py`, `test_cors.py` 통과 |
| 선행 | `AUTH-1-P1` | `feat(auth): AUTH-1-P1 JWT 검증 및 ApiError 공통 오류 처리` | **완료** | `a1fa5c3` (`1f304b6`) | `test_auth_jwt.py` 32건 통과 |
| 1 | `AUTH-1-P2` | `feat(auth): AUTH-1-P2 users 테이블 마이그레이션 및 DB 실행 헬퍼(run_db)` | **완료** | `9d766ee` | `alembic upgrade head` + `pytest -W error` 54건 통과 |
| 2 | `AUTH-1-P3` | `feat(auth): AUTH-1-P3 POST /api/v1/auth/session 및 GET /api/v1/me 구현` | **완료** | `661a054` | `alembic upgrade head` + `pytest -W error` 62건 통과 |
| 3 | `AUTH-1-P4~P6` | `feat(auth): AUTH-1-P4~P6 앱 OAuth 어댑터·AuthProvider·apiFetch·로그인 화면(후보 B)` | **완료** | `9f92bd6` | `tsc --noEmit` 0오류 + `jest` 4스위트 9건 통과 + `expo export --platform web` 성공 |
| 4 | `DB-M1-CORE` | `feat(db): M1 핵심 테이블(0002) 및 M2 확장 테이블(0003) 마이그레이션·초기 시드` | **완료** | `59b2af1` | 28개 전 테이블 RLS(`relrowsecurity=true`, 정책 0개)·왕복 마이그레이션·시드 검증 (`pytest -W error` 66건 통과) |
| 5 | `AUTH-2-3` | `feat(auth): AUTH-2·3 내 설정(반경·동의) 조회/변경, 로그아웃 정화 및 회원 탈퇴(DELETE /api/v1/me)` | **완료** | `d467c9d` | 백엔드 `pytest -W error` 69건 통과 + 모바일 `tsc`·`jest` 10건·`expo export --platform web` 통과 |

### Phase 2 ~ Phase 7 (대기)

Step·순서의 원본은 [상용 서비스 계획 §3](상용_서비스_계획.md)이다. 아래는 그 표의 요약이며 여기서 Step을 새로 만들지 않는다(2026-11-15 문서 리뷰에서 이 절이 계획과 다른 Step ID·순서를 적고 있던 것을 바로잡음, `DEF-007`).

| Phase | 순서 | Step | 상태 |
| :---: | :---: | :--- | :---: |
| 2 (M1 조회) | 6~9 | `LIB-0` → `LIB-1` → `LIB-2` → `LIB-3` | 대기 |
| 3 (M1 방문·광장) | 10~13 | `VISIT-1` → `VISIT-2` → `LOCAL-1` → `LOCAL-2` | 대기 |
| 4 (M1 반납 비서, **M1 완결 관문**) | 14~15 | `LOAN-1-2` → `LOAN-3` | 대기 |
| 5 (M2 방문 확장·기록) | 16~19 | `READ-1-2` → `VISIT-3` → `VISIT-4` → `LOCAL-3` | 대기 |
| 6 (M2 모임·프로필·운영) | 20~23 | `CLUB-1` → `CLUB-2` → `AUTH-4` → `LOCAL-4` | 대기 |
| 7 (통합·산출물) | 24~25 | `RELEASE-1` → `RELEASE-2` | 대기 |

---

## 3. 완료된 Step 상세 기록 (Phase 1 전 구간)

### [Step 1] `AUTH-1-P2` — `users` 테이블 마이그레이션 및 DB 실행 헬퍼(`run_db`)
- **커밋 SHA**: `9d766ee80fbac3ecc6d1f8e12e70e5d0621aef26` (`9d766ee`)
- **포함 파일 (7개, `AUTH-1_계약서.md` P2 100% 일치)**:
  - `server/app/db.py`, `server/alembic.ini`, `server/migrations/env.py`, `server/migrations/script.py.mako`, `server/migrations/versions/0001_users.py`, `server/tests/conftest.py`, `server/tests/test_auth_storage.py`
- **검증**: `alembic upgrade head` + `pytest -W error` (`54 passed in 0.38s`)

### [Step 2] `AUTH-1-P3` — `POST /api/v1/auth/session` 및 `GET /api/v1/me` 구현
- **커밋 SHA**: `661a0542c835d2d2911fbefbe8c2a659fb5ba634` (`661a054`)
- **포함 파일 (5개, `AUTH-1_계약서.md` P3 파트)**:
  - `server/app/auth.py`, `server/app/main.py`, `server/tests/test_auth_session.py`, `.env.example`, `.github/workflows/ci.yml`
- **핵심 구현**:
  - `POST /api/v1/auth/session`: `INSERT INTO users (id) VALUES (:id) ON CONFLICT (id) DO NOTHING RETURNING id`로 멱등 등록(`is_new` 반환), 본문 `user_id` 완전 무시(C6), 탈퇴 계정 `403 ACCOUNT_WITHDRAWN` 차단
  - `GET /api/v1/me`: `Depends(get_current_user)`로 미등록 계정 `401 AUTH_NOT_REGISTERED`, 탈퇴 계정 `403 ACCOUNT_WITHDRAWN`, 정상 계정 `200` 반환
- **검증**: `alembic upgrade head` + `pytest -W error` (`62 passed in 0.55s`)

### [Step 3] `AUTH-1-P4~P6` — 앱 OAuth 어댑터·`AuthProvider`·`apiFetch`·로그인 화면(후보 B)
- **커밋 SHA**: `9f92bd691d4df1cf4dc02d7cc9731ba4b07e520c` (`9f92bd6`)
- **포함 파일 (16개, `AUTH-1_계약서.md` P4~P6 100% 일치)**:
  - `mobile/.env.example`, `mobile/app.json`, `mobile/package.json`, `mobile/package-lock.json`, `mobile/jest.config.js`, `mobile/app/_layout.tsx`, `mobile/app/index.tsx`, `mobile/app/login.tsx`, `mobile/src/auth/platform.ts`, `mobile/src/auth/supabase.ts`, `mobile/src/auth/apiFetch.ts`, `mobile/src/auth/AuthProvider.tsx`, `mobile/src/auth/__tests__/platform.test.ts`, `mobile/src/auth/__tests__/apiFetch.test.ts`, `mobile/src/auth/__tests__/AuthProvider.test.tsx`, `mobile/src/auth/__tests__/login.test.tsx`
- **핵심 구현**:
  - `platform.ts`: 5대 플랫폼 분기(세션 저장소 Web `localStorage` vs Native `AsyncStorage`(계약 A8 — 2026-11-15 리뷰에서 "`expo-secure-store`"였던 오기를 바로잡음, `DEF-020`), `detectSessionInUrl`, Google OAuth Web 리디렉트 vs Native PKCE 브라우저 코드 교환, Apple Sign-In iOS 네이티브 vs Web/Android 비노출, `AppState` 포그라운드 토큰 자동 갱신)
  - `apiFetch.ts`: `401 AUTH_EXPIRED` 시 `refreshSession()` 1회 후 재전송, `401 AUTH_NOT_REGISTERED` 시 `rawRegisterSession` 1회 후 재전송(무한 루프 방지)
  - `AuthProvider.tsx`: `POST /api/v1/auth/session`이 `200`을 반환하기 전까지 `signedIn` 전환 금지(C7), 세대 카운터로 언마운트/레이스 방어
  - `login.tsx`: 후보 B(Forest & Cream) 시안 기반 로그인 화면, 진행 중 중복 탭 차단, 사용자 취소 시 에러 미표시
- **검증**: `npx tsc --noEmit` (0 errors), `npx jest --runInBand` (4 suites, 9 passed), `npx expo export --platform web` (성공)

### [Step 4] `DB-M1-CORE` — M1 핵심 테이블(`0002`) 및 M2 확장 테이블(`0003`) 마이그레이션·초기 시드
- **커밋 SHA**: `59b2af1d53463686be8281c5a4f4a0710557941a` (`59b2af1`)
- **포함 파일 (4개)**:
  - `server/migrations/versions/0002_m1_core.py`: M1 13개 테이블(`user_profiles`, `user_settings`, `libraries`, `books`, `availability_observations`, `popular_books_cache`, `provider_daily_usage`, `loan_plans`, `loans`, `library_return_stats`, `posts`, `post_reactions`, `post_bookmarks`), 도메인 CHECK 제약(R1~R15), 부분 UNIQUE 인덱스, 전 테이블 RLS 활성화
  - `server/migrations/versions/0003_m2_extensions.py`: M1 테이블 M2 확장 컬럼(`users.role`, `user_profiles.bio/avatar_url`, `libraries.look_preset/look_is_manual`, `posts.template_key/reading_log_id/like_count`) 및 M2 14개 신규 테이블(`reading_logs`, `guestbook_entries`, `visit_stamps`, `shelf_themes`, `shelf_theme_books`, `clubs`, `club_participants`, `club_comments`, `club_reviews`, `feed_bookmarks`, `user_follows`, `notifications`, `moderation_reports`, `user_penalties`), 전 테이블 RLS 활성화
  - `server/app/seed.py`: 도서관 4곳(4종 룩 프리셋), 도서 6권, 3갈래 소장 관측(`AVAILABLE`, `ON_LOAN`, `UNAVAILABLE`, `UNKNOWN`), 전국·도서관 인기 도서 캐시, 오늘의 서가 테마 1종 멱등 시드(`seed_reference_data`)
  - `server/tests/test_db_schema_and_seed.py`: 28개 전 테이블 존재·RLS 활성화(`relrowsecurity=true`, 정책 0개)·`library_return_stats` 개인 식별 컬럼 부재(R15)·CHECK 제약(R1·R3·R4)·시드 멱등성·`downgrade base -> upgrade head` 왕복 검증
- **검증**: `alembic upgrade head` + `pytest -W error` (`66 passed in 0.91s`)

### [Step 5] `AUTH-2-3` — 내 설정 조회/변경, 로그아웃 정화 및 회원 탈퇴(`DELETE /api/v1/me`)
- **커밋 SHA**: `d467c9d4be3c4a47ce8979540903a40a951c4820` (`d467c9d`)
- **포함 파일 (8개)**:
  - `server/app/auth.py`, `server/app/main.py`, `server/app/routers/me.py`, `server/tests/test_me.py`, `mobile/src/auth/apiFetch.ts`, `mobile/src/auth/AuthProvider.tsx`, `mobile/src/auth/__tests__/AuthProvider.test.tsx`, `mobile/src/auth/__tests__/login.test.tsx`
- **핵심 구현**:
  - `POST /api/v1/auth/session` 시 `user_profiles` 행이 없으면 `이웃-${sub 앞 4자리}`로 자동 생성(Q-55)
  - `GET /api/v1/me/settings`: 행이 없으면 DB 쓰기 없이 기본값(`nearby_radius_km: 3`, `return_stats_consent: False`, `return_stats_consent_at: None`) 반환
  - `PATCH /api/v1/me/settings`: `nearby_radius_km` (`3` 또는 `5`, 그 외 `422 VALIDATION_ERROR`) 및 `return_stats_consent` 변경·동의 시각 기록/초기화
  - `DELETE /api/v1/me`: 단일 트랜잭션에서 작성 `posts`를 `withdrawn`으로, `guestbook_entries`를 `deleted`로 전환하고 개인 전용 데이터(`loans`, `loan_plans`, `reading_logs`, `visit_stamps`, `post_bookmarks`, `post_reactions`, `feed_bookmarks`, `notifications`, `user_follows`, `user_settings`) 즉시 삭제, `user_profiles` 익명화(`탈퇴한 이웃`), `users.status = 'withdrawn'` 전환(Q-23, AC-DELETE, AC-ISOLATION)
  - 모바일 `AuthProvider.tsx`: `registerSignOutCleanup`, `signOut()`, `withdrawAccount()` 추가 및 테스트 완비
- **검증**:
  - 백엔드: `cd server && APP_ENV=test /tmp/uvenv/bin/uv run pytest -W error` → `69 passed in 1.29s`
  - 모바일: `cd mobile && npx tsc --noEmit && npx jest --runInBand && npx expo export --platform web` → `4 suites, 10 passed`, 웹 번들 export 성공

---

## 4. Phase 1 적대적 리뷰어(타 LLM) 및 Phase 2 착수 인계 블록

```text
[Phase 1 적대적 리뷰(Adversarial Review) 가이드]
검토 대상 커밋 구간 (Phase 1 전체 5개 기능 커밋):
  1. 9d766ee — feat(auth): AUTH-1-P2 users 테이블 마이그레이션 및 DB 실행 헬퍼(run_db)
  2. 661a054 — feat(auth): AUTH-1-P3 POST /api/v1/auth/session 및 GET /api/v1/me 구현
  3. 9f92bd6 — feat(auth): AUTH-1-P4~P6 앱 OAuth 어댑터·AuthProvider·apiFetch·로그인 화면(후보 B)
  4. 59b2af1 — feat(db): M1 핵심 테이블(0002) 및 M2 확장 테이블(0003) 마이그레이션·초기 시드
  5. d467c9d — feat(auth): AUTH-2·3 내 설정(반경·동의) 조회/변경, 로그아웃 정화 및 회원 탈퇴(DELETE /api/v1/me)

리뷰어 실행 명령:
  1. docker compose up -d --wait db
  2. cd server && APP_ENV=test /tmp/uvenv/bin/uv run alembic downgrade base && APP_ENV=test /tmp/uvenv/bin/uv run alembic upgrade head
  3. cd server && APP_ENV=test /tmp/uvenv/bin/uv run pytest -W error
  4. cd mobile && npx tsc --noEmit && npx jest --runInBand && npx expo export --platform web && rm -rf dist

중점 감사 포인트 (계획/하네스_엔지니어링_규칙.md §5):
  - AUTH-1_계약서.md P2 허용 파일 경계 및 C1~C7 계약 준수 여부
  - 05_ERD_및_DB설계서.md의 28개 테이블(M1 14 + M2 14) 스키마·제약·RLS(정책 0개) 일치 여부
  - DELETE /api/v1/me 탈퇴 시 타인(User B) 데이터 격리(AC-ISOLATION) 및 본인 데이터 즉시 삭제(AC-DELETE) 완결성
  - 발견된 결함이 있으면 즉시 수정 후 아래 §5 표와 계획/하네스_엔지니어링_규칙.md §6(DEF-XXX)에 기록할 것.

[Phase 2 착수 인계 (리뷰 통과 후 다음 세션 목표)]
다음 작업 Phase / Step:
  - Phase 2 (6번 LIB-0 -> 7번 LIB-1 -> 8번 LIB-2 -> 9번 LIB-3)
  - 첫 착수 Step: 6번 LIB-0 — feat(lib): LIB-0 도서·도서관·소장·인기도서 공통 조회 엔진(캐시·상한·시드 Fallback)
    (06 #7~#15. 대상: server/app/services/provider_engine.py, server/app/routers/books.py, server/app/routers/libraries.py,
     server/app/policy.py, server/tests/test_lib_engine.py 외 — 계획 §3 Phase 2 표와 §3.1 공통 완료 조건)
  - 추천 모델 / 권장 Effort: 고성능 모델(Claude Fable 또는 Codex Astra) / 높음
    (이유: 외부 API 3갈래 Fallback, DB 트랜잭션 밖 I/O 분리 H-ARCH-03, Owner: D/C 커밋 분리 H-GIT-05)
  - Phase 2 완료 후 적대적 리뷰: 구현과 다른 고성능 모델(Astra/Fable) / 높음
  - 착수 전 읽기: 02 §0 LIB-01~07·§9, 05 §3.1(libraries·books·availability_observations·popular_books_cache·provider_daily_usage)·§11, 06 §2.2·§3
  - Phase 1 리뷰(2026-11-15) 결과: DEF-008 구현 완료, DEF-010은 문서 가드(H-GIT-04)로 종결.
    LIB-1 착수 전 처리: DEF-019(공용 디자인 토큰 모듈 + login.tsx 이전).
    LIB-0부터 새 쓰기 엔드포인트는 트랜잭션 첫 SQL로 lock_active_user(H-ARCH-11).
```

---

## 5. Phase별 타 LLM 적대적 리뷰 및 조치 기록

| Phase | 리뷰 수행 모델 / 일시 | 검토 범위 (커밋 구간) | 발견된 결함 (`DEF-ID`) | 조치 및 수정 커밋 | 최종 판정 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **Phase 1** | 구현: 이전 세션 / 리뷰: Claude Opus 5.5(`claude-opus-5-5`), 2026-11-15, mac — 구현과 다른 세션 | `9d766ee` ~ `d467c9d` (`AUTH-1-P2` ~ `AUTH-2-3`) | 구현 중 자체 포착 `DEF-001`~`006`. 리뷰: `DEF-008`(S2), `DEF-013`(S2), `DEF-014`(S2), `DEF-015`(S2), `DEF-016`(S3), `DEF-017`(S2), `DEF-018`(S2), `DEF-019`(S2), `DEF-020`(S3). S1 0건 | `d145fe5`(013·014), `83b5540`(008), `c309470`(015), `dbed0a0`(016), `eeffa04`(017), `f70e77f`(018), `1ba19f4`(06 §7 필드 표). `DEF-019`는 기한 `LIB-1` 착수 전 | **통과** (S1 0, S2는 수정 또는 기한) |
| **문서(전 Phase)** | Claude(Fable 5.2) / 2026-11-15 — 문서만 정적 리뷰, 코드·테스트 실행 없음 | `CLAUDE.md`·`AGENTS.md`·`GEMINI.md`, `계획/*`, `개발산출물/02·05·06`, `인수인계_메모` | `DEF-007`(계획↔작업 기록 Step·순서 불일치와 의존 역전 3건), `DEF-008`(철회 세션 미검증), `DEF-009`(진입 파일 gitignore), `DEF-010`(M1·M2 마이그레이션 한 커밋), `DEF-011`(02↔06 패널티 자동 부과 모순), `DEF-012`(문서가 없는 기능·틀린 개수를 단정) | 문서 수정으로 조치: 계획 §3 재배열·공통 완료 조건, 02 §9 미결 처리표, 05 머리·§11, 06 #62~#72·오류 코드, 하네스 `H-GIT-04`·`H-DOC-*`·판정 기준·편차 목록. **코드 조치가 남은 것: `DEF-008`** | **문서 조치 완료 / Phase 1 코드 리뷰는 여전히 대기** |

### Phase 1 코드 리뷰 상세 (2026-11-15, Claude Opus 5.5)

- **실행한 명령과 결과**(리뷰어가 다시 실행):
  - `docker compose up -d --wait db` → Healthy. `uv`는 PATH에 없어 `/tmp/uvenv/bin/uv`(H-ENV-01)
  - `APP_ENV=test uv run alembic downgrade base` rc=0 → `upgrade head` rc=0 → `alembic current` = `0003 (head)`
  - `APP_ENV=test uv run pytest -W error`: 리뷰 전 `69 passed` → 수정 후 `79 passed`
  - `mobile`: `npx tsc --noEmit` 0오류, `npx jest --runInBand` 리뷰 전 `10 passed` → 수정 후 `12 passed`, `npx expo export --platform web` 성공(출력은 scratchpad, `dist` 미생성)
- **§5 7항목 판정**:
  1. 계약 대조: 커밋별 파일 = AUTH-1 계약서 P2(7)·P3(5)·P4+P5+P6(16) 목록과 일치. 등록 라우트 6개 = 06 #1~#6. C3·C6 화면 문구 8개 코드에 있음. `Platform.OS`는 `src/auth/platform.ts`에만. 06 §7 #2~#6 필드 표를 코드와 대조해 채움(`1ba19f4`). `detail` 형식 불일치 → `DEF-016`
  2. 동시성: 설정 PATCH lost update 재현(radius 5→3) → `DEF-013`. 탈퇴와 쓰기 경쟁으로 탈퇴 계정에 `user_settings` 재생성 재현 → `DEF-014`. `POST /auth/session` 동시 등록은 기존 시험으로 1행 확인
  3. 인증·격리: 무헤더·소문자 `bearer`·빈 Bearer·이중 공백·`role` 누락·`nbf` 미래·`sub` 비문자열 모두 계약 코드로 거부. 미등록 계정은 #4~#6 모두 401 `AUTH_NOT_REGISTERED`, 탈퇴 계정은 403. 철회 세션 미검증 → `DEF-008` 구현. 앱 `apiFetch` 토큰 유출 → `DEF-017`
  4. 스키마·RLS·왕복: 왕복 rc=0, 28개 테이블 RLS·정책 0(기존 시험). `users` FK 21개 칸을 05 §11.1과 대조, `club_comments.delete_requested_by` 행 보강
  5. 테스트 무결성: 변형 7개 중 3개 생존(팔로우 역방향 삭제 제거, 재동의 시각 유지 제거, 프로필 익명화 제거) → `DEF-015`로 보강 뒤 모두 실패 확인. 수정 시험(013·014·008·017·018)은 수정 전 코드에서 실패함을 확인
  6. 문서 정합: 실제 컬럼 208개 중 05 본문에 이름이 없는 것 5개(`loan_plans.memo`, `loans.due_on_assumed`, `posts.image_kind`·`image_value`·`overlay_text` — 주니어 영역은 한글 골격 서술, 원본은 마이그레이션이라 S3 기록만). 작업 기록 §3의 저장소 오기 → `DEF-020`
  7. 불변 조건·AC: 10개 조건 대조 — 색 토큰 하드코딩(`login.tsx`) → `DEF-019`. 나머지 Phase 1 해당 조건 충족. **미검증(통과로 세지 않음)**: AC-AUTH·AC-DELETE의 "기기 예약 알림" 부분(알림 기능 없음, `LOAN-1-2`), 업로드 파일 삭제(`LOCAL-1`), C4 실기기·실 Supabase 로그인(웹·Android·iOS), 운영 Supabase에서 서버 DB 계정의 `auth.sessions` SELECT 권한(`RELEASE-1`)


---

## 6. 본 레포(`axteamc/localone`) 역이식 기록

판정 기준은 [하네스 `H-GIT-05`·`H-GIT-06`, §7 #7](하네스_엔지니어링_규칙.md). 새로 옮길 때마다 한 줄 더한다.

| 날짜·PC | 본 레포 PR(브랜치) | 옮긴 libtalk 커밋 | 손댄 것 | 상태 |
| :--- | :--- | :--- | :--- | :--- |
| 2026-11-16 win | #56 `feat/auth-1-part2` | `9d766ee` | 없음 | 머지 `a013df6` |
| 2026-11-16 win | #57 `feat/auth-1-part3` | `661a054` | `ci.yml` 충돌 → 조건 없는 `alembic upgrade head` | #57은 앞 브랜치로 머지(main 미반영) → #63으로 다시 올려 머지 `366d6e6` |
| 2026-11-16 win | #58 `feat/auth-1-part4` | `9f92bd6` 중 P4 파일 7개 | 계약 P2 파트별 파일로 분할 | #64로 다시 올려 머지 `6e54afc` |
| 2026-11-16 win | #59 `feat/auth-1-part5` | `9f92bd6` 중 P5 파일 5개 + `eeffa04` + `f70e77f` | DEF-018 시험 파일에서 AUTH-2·3 탈퇴 시험 제외 + 리뷰 수정 `e04f82f`(DEF-021) | #67로 다시 올려 머지 `cd3cb6a` |
| 2026-11-16 win | #60 `feat/auth-1-part6` | `9f92bd6` 중 P6 파일 4개 | 리뷰 수정 `33840b1`(DEF-021) | #68로 다시 올려 머지 `7bf6d59` |
| 2026-11-16 win | #80 `feat/auth-1-apple-toggle` | `d6bb42f` (본 레포 `9fb4a0c` 동기화) | 없음 (`AUTH-1-P7` 5파일 일치) | PR #80 CI 통과, 머지 대기 |

- 본 레포에서 다섯 브랜치 모두 시험 통과(서버 54→62 passed, 앱 jest 11 passed, tsc·웹 export 통과). 실로그인(C7 외부 설정)·실기기는 미확인.
- 2026-11-16 리뷰: 스택 PR #57~#60이 실수로 앞 브랜치로 머지되어 main에 안 들어감 → 같은 커밋을 main 대상 #63·#64·#67·#68로 다시 올림. 리뷰에서 DEF-021을 찾아 양쪽에 같은 수정(libtalk `c2a5f0a`). 본 레포 코드·커밋에는 DEF-019로 적힘(번호 충돌).
- 남은 D 몫(발췌 이식 후보): `83b5540`의 세션 확인(`session_is_alive`·`auth_session_check`), `d145fe5`의 `lock_active_user`. AUTH-2·3 본체는 주니어 테이블이 본 레포에 머지된 뒤.
