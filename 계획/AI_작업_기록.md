# AI 작업 기록 및 세션 인계 공유 문서 (Multi-LLM Shared Work Log)

> **문서 성격**: 이 문서는 여러 세션과 여러 LLM 모델(구현 AI ↔ Phase별 적대적 리뷰·테스트 AI)이 동네한권(`choise-hun/libtalk`)의 구현 상태, 검증 결과, 다음 작업 인계 사항을 끊김 없이 공유하는 **단일 작업 상태판(Shared State Board)**이다.
> **참조 문서**:
> - 구현 및 역이식 규칙: [CLAUDE.md](../CLAUDE.md)
> - 결함 방지 및 적대적 리뷰 규칙: [하네스_엔지니어링_규칙.md](하네스_엔지니어링_규칙.md)
> - 전체 커밋 로드맵: [상용_서비스_계획.md](상용_서비스_계획.md)

---

## 1. 현재 진행 위치 요약

- **현재 Phase**: **Phase 1 — DB 스키마·시드 기반 및 인증(`AUTH-1~3`) 완결**
- **직전 완료 Step**: Phase 1 — **1번 `AUTH-1-P2`** (`9d766ee`, `users` 테이블 마이그레이션 및 `run_db`)
- **다음 착수 Step**: Phase 1 — **2번 `AUTH-1-P3`** (`POST /api/v1/auth/session` 및 `GET /api/v1/me` 구현)
- **Phase 1 적대적 리뷰 상태**: Phase 1(1~5번 커밋) 완료 후 타 LLM 적대적 리뷰 및 통합 테스트 실시 예정

---

## 2. Phase 1 ~ Phase 7 전체 커밋 진행 현황표

### Phase 1. DB 스키마·시드 기반 및 인증(`AUTH-1~3`) 완결
| 순서 | Step ID | 커밋 메시지 / 범위 | 상태 | 커밋 SHA | 검증 결과 |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 선행 | `INIT` | `SET-0~SET-5` 서버·앱 뼈대, CORS, 번들 ID, CI | **완료** | `1353eb4` 이전 | `test_ready.py`, `test_cors.py` 통과 |
| 선행 | `AUTH-1-P1` | `feat(auth): AUTH-1-P1 JWT 검증 및 ApiError 공통 오류 처리` | **완료** | `a1fa5c3` (`1f304b6`) | `test_auth_jwt.py` 32건 통과 |
| 1 | `AUTH-1-P2` | `feat(auth): AUTH-1-P2 users 테이블 마이그레이션 및 DB 실행 헬퍼(run_db)` | **완료** | `9d766ee` | `alembic upgrade head` + `pytest -W error` 54건 통과 |
| 2 | `AUTH-1-P3` | `feat(auth): AUTH-1-P3 POST /api/v1/auth/session 및 GET /api/v1/me 구현` | **다음 착수** | — | 대기 |
| 3 | `AUTH-1-P4~P6` | `feat(auth): AUTH-1-P4~P6 앱 OAuth 어댑터·AuthProvider·apiFetch·로그인 화면(후보 B)` | 대기 | — | 대기 |
| 4 | `DB-M1-CORE` | `feat(db): M1 핵심 테이블(0002) 및 M2 확장 테이블(0003) 마이그레이션·초기 시드` | 대기 | — | 대기 |
| 5 | `AUTH-2-3` | `feat(auth): AUTH-2·3 내 설정(반경·동의) 조회/변경, 로그아웃 정화 및 회원 탈퇴(DELETE /api/v1/me)` | 대기 | — | 대기 |

*(Phase 2 ~ Phase 7의 6번~25번 Step은 [상용_서비스_계획.md §3](상용_서비스_계획.md) 기준 대기 중)*

---

## 3. 완료된 Step 상세 기록

### [Step 1] `AUTH-1-P2` — `users` 테이블 마이그레이션 및 DB 실행 헬퍼(`run_db`)
- **커밋 SHA**: `9d766ee80fbac3ecc6d1f8e12e70e5d0621aef26` (`9d766ee`)
- **포함 파일 (7개, `AUTH-1_계약서.md` P2 100% 일치)**:
  1. `server/app/db.py`: `async def run_db(engine: Engine, fn: Callable[[Connection], T]) -> T` 구현 (`asyncio.to_thread` + `with engine.begin() as conn:`, 연결 오류 시 `ApiError(503, "DB_UNAVAILABLE", "데이터베이스에 연결하지 못했어요.")`, 도메인/제약 예외는 롤백 후 원형 전파)
  2. `server/alembic.ini`: `script_location = %(here)s/migrations`, 별도 DB URL 미기재
  3. `server/migrations/env.py`: `app.settings.get_settings().database_url` 단일 참조
  4. `server/migrations/script.py.mako`: Alembic 마이그레이션 템플릿
  5. `server/migrations/versions/0001_users.py`: `users` 테이블(`id uuid PK`, `status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'withdrawn'))`, `created_at timestamptz NOT NULL DEFAULT now()`) 생성 및 `ALTER TABLE users ENABLE ROW LEVEL SECURITY`(정책 0개), `downgrade()`에서 `op.drop_table("users")`
  6. `server/tests/conftest.py`: 세션 시작 시 `alembic upgrade head` 1회 실행, DB 테스트 전후 `TRUNCATE TABLE users CASCADE`, `refusing_db_url` 소켓 픽스처, `AUTH-1-P3`에서도 재사용할 EC P-256 `jwt_signing_key`·`fake_jwks_client`·`make_token` 픽스처 제공
  7. `server/tests/test_auth_storage.py`: P5 필수 테스트 4종(`test_users_status_check`, `test_users_rls_enabled`, `test_migration_round_trip`, `test_run_db_commit_rollback`) 구현
- **실행 검증 명령 및 결과**:
  - `docker compose up -d --wait db` → `Container libtalk-db-1 Healthy`
  - `cd server && APP_ENV=test /tmp/uvenv/bin/uv run alembic upgrade head` → 성공 (`0001` 적용)
  - `cd server && APP_ENV=test /tmp/uvenv/bin/uv run pytest -W error tests/test_auth_storage.py tests/test_ready.py tests/test_cors.py` → `22 passed in 0.27s`
  - `cd server && APP_ENV=test /tmp/uvenv/bin/uv run pytest -W error` → `54 passed in 0.38s`

---

## 4. 다음 Step 인계 블록 (`AUTH-1-P3`)

```text
다음 작업 ID / 목표: Phase 1 - 2번 AUTH-1-P3 (POST /api/v1/auth/session 및 GET /api/v1/me 구현)
기준 문서:
  - 개발산출물/명세/AUTH-1_계약서.md (C1·C2·C3·C5·C6·C7 및 P2 AUTH-1-P3 머리말, P4 골격, P5 필수 테스트)
  - 계획/상용_서비스_계획.md §3 Phase 1 (2번 행)
  - 계획/하네스_엔지니어링_규칙.md (H-GIT-01~03, H-ENV-01~05, H-ARCH-01~05)
수정/생성 허용 파일 (본 레포 AUTH-1-P3 계약 기준 5개):
  1. server/app/auth.py (get_current_user 및 router: POST /api/v1/auth/session, GET /api/v1/me 추가; 기존 P1 JWT 검증 로직 보존)
  2. server/app/main.py (# ── [auth-D] ── 블록 안에 auth 라우터 등록)
  3. server/tests/test_auth_session.py (P5 필수 테스트: test_session_creates_user_once, test_session_concurrent_same_user_one_row, test_session_ignores_body_user_id, test_auth_db_failure_is_503, test_me_returns_own_user, test_me_not_registered, test_withdrawn_user_forbidden, test_invalid_token_does_not_create_user)
  4. .env.example (SUPABASE_URL= 추가)
  5. .github/workflows/ci.yml (서버 job의 alembic upgrade head 단계 정식화)
검증 명령:
  - docker compose up -d --wait db
  - cd server && APP_ENV=test /tmp/uvenv/bin/uv run alembic upgrade head
  - cd server && APP_ENV=test /tmp/uvenv/bin/uv run pytest -W error
커밋 메시지:
  - feat(auth): AUTH-1-P3 POST /api/v1/auth/session 및 GET /api/v1/me 구현
```

---

## 5. Phase별 타 LLM 적대적 리뷰 및 조치 기록

| Phase | 리뷰 수행 모델 / 일시 | 검토 범위 (커밋 구간) | 발견된 결함 (`DEF-ID`) | 조치 및 수정 커밋 | 최종 판정 |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **Phase 1** | *(Phase 1 완료 후 기록 예정)* | `AUTH-1-P2` ~ `AUTH-2-3` | — | — | 대기 |
