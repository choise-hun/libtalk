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
- **현재 관문**: **Phase 1 타 LLM 적대적 리뷰(Adversarial Review) 및 테스트 대기**
- **다음 착수 Phase / Step (리뷰 통과 후)**: **Phase 2 — 조회 엔진(`LIB-1·2`), 빌릴 예정(`LIB-3`), 반납 비서(`LOAN-1·2`)** (6번 `LIB-1` 도서 검색·상세·추천/인기 도서·예스24 구매 링크부터 착수)

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
- **Phase 2 (`6~9번`)**: `LIB-1` → `LIB-2` → `LIB-3` → `LOAN-1-2`
- **Phase 3 (`10~11번`)**: `LOCAL-1-2` → `VISIT-1-2`
- **Phase 4 (`12~14번`)**: `READ-1-2` → `VISIT-3` → `VISIT-4`
- **Phase 5 (`15~17번`)**: `CLUB-1` → `CLUB-2` → `CLUB-3`
- **Phase 6 (`18~20번`)**: `AUTH-4` → `USR-4-6` → `LOCAL-4`
- **Phase 7 (`21~25번`)**: `APP-NAV-THEME` → `APP-LIB-LOAN-UI` → `APP-VISIT-CLUB-UI` → `APP-SNS-ME-UI` → `E2E-HARDENING`

---

## 3. 완료된 Step 상세 기록 (Phase 1 전 구간)

### [Step 1] `AUTH-1-P2` — `users` 테이블 마이그레이션 및 DB 실행 헬퍼(`run_db`)
- **커밋 SHA**: `9d766ee80fbac3ecc6d1f8e12e70e5d0621aef26` (`9d766ee`)
- **포함 파일 (7개, `AUTH-1_계약서.md` P2 100% 일치)**:
  - `server/app/db.py`, `server/alembic.ini`, `server/migrations/env.py`, `server/migrations/script.py.mako`, `server/migrations/versions/0001_users.py`, `server/tests/conftest.py`, `server/tests/test_auth_storage.py`
- **검증**: `alembic upgrade head` + `pytest -W error` (`54 passed in 0.38s`)

### [Step 2] `AUTH-1-P3` — `POST /api/v1/auth/session` 및 `GET /api/v1/me` 구현
- **커밋 SHA**: `661a0542c835d2d2911fbefbe8c2a659fb5ba634` (`661a054`)
- **포함 파일 (5개, `AUTH-1_계약서.md` P2 100% 일치)**:
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
  - `platform.ts`: 5대 플랫폼 분기(세션 저장소 Web `localStorage` vs Native `expo-secure-store`, `detectSessionInUrl`, Google OAuth Web 리디렉트 vs Native PKCE 브라우저 코드 교환, Apple Sign-In iOS 네이티브 vs Web/Android 비노출, `AppState` 포그라운드 토큰 자동 갱신)
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
  - 05_ERD_및_DB설계서.md의 28개 테이블 스키마·제약·RLS(정책 0개) 일치 여부
  - DELETE /api/v1/me 탈퇴 시 타인(User B) 데이터 격리(AC-ISOLATION) 및 본인 데이터 즉시 삭제(AC-DELETE) 완결성
  - 발견된 결함이 있으면 즉시 수정 후 아래 §5 표와 계획/하네스_엔지니어링_규칙.md §6(DEF-XXX)에 기록할 것.

[Phase 2 착수 인계 (리뷰 통과 후 다음 세션 목표)]
다음 작업 Phase / Step:
  - Phase 2 (6번 LIB-1 -> 7번 LIB-2 -> 8번 LIB-3 -> 9번 LOAN-1-2)
  - 첫 착수 Step: 6번 LIB-1 — feat(books): LIB-1 도서 검색(20건)·상세·추천/인기 도서·예스24 구매 링크 및 일일 쿼터 가드
    (대상: server/app/providers/books.py, server/app/routers/books.py, server/tests/test_books.py)
```

---

## 5. Phase별 타 LLM 적대적 리뷰 및 조치 기록

| Phase | 리뷰 수행 모델 / 일시 | 검토 범위 (커밋 구간) | 발견된 결함 (`DEF-ID`) | 조치 및 수정 커밋 | 최종 판정 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **Phase 1** | *(타 LLM 적대적 리뷰 대기)* | `9d766ee` ~ `d467c9d` (`AUTH-1-P2` ~ `AUTH-2-3`) | 구현 중 자체 포착: `DEF-001`~`DEF-006` | 하네스 규칙(`H-ENV`, `H-GIT`, `H-ARCH`) 반영 완료 | **리뷰 준비 완료** |
