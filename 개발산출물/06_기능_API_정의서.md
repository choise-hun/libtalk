# 06. 기능·API 정의서 (단독 마스터 예비본: M1 + M2 전 범위 통합)

> 상태: **M1(1~30번) + M2(31~72번) 전체 엔드포인트 및 공통 오류 코드 확정.** 구현된 것은 1~6번뿐이다(2026-11-15 기준, 진행은 [AI 작업 기록](../계획/AI_작업_기록.md)).
> **역이식 호환 원칙**: §2.1~§2.5의 M1 30개 엔드포인트와 §3의 공통 오류 코드는 본 협업 레포(`axteamc/localone`)와 경로·메서드·응답 규격을 100% 동일하게 유지하며, M2 기능(독서 기록·방명록·오늘의 서가·방문 스탬프·모임·프로필 3탭·팔로우·알림함·신고/운영)은 §2.6~§2.10에 확장 정의한다.

## 단독 예비본 우선 규칙 (2026-11-15)

§1~§2.5·§4~§6은 본 레포 기준선 사본이라 아래 문장이 남아 있다. 단독 예비본에서는 오른쪽이 이긴다.

| M1 절의 문장 | 단독 예비본에서 |
| --- | --- |
| `미확인(임시)` + Q-번호, "계약서에서 정한다", 담당 A·B·C·D | [05 §11](05_ERD_및_DB설계서.md)·[02 §9](02_요구사항_정의서.md)의 값으로 구현. 요청·응답 필드는 구현 Step이 이 문서에 표로 더한다(§5) |
| §2.1 "닉네임을 바꾸는 엔드포인트는 두지 않는다" | #55(`PATCH /me/profile`)로 바꾼다 |
| §2.4 "내 게시물 목록·북마크 모음·좋아요 모음 엔드포인트는 두지 않는다" | #58 |
| #26 "`sort=popular`는 열지 않는다" | 연다: `like_count DESC, published_at DESC, id DESC`(Q-31) |
| #30 게시물 북마크 `미확인(임시)` | 그대로 구현(M1 호환 경로). #59의 `target_type=post`는 #30과 **같은 저장소(`post_bookmarks`)**를 쓴다 |
| #9 "M1은 테마 표가 없어 항상 인기 도서" | `shelf_themes`의 활성 테마를 먼저 본다(02 §9 Q-47) |
| §2.1 "철회된 세션의 쓰기 거부는 `session_id`로 확인" | 구현(`DEF-008`): `get_current_user`가 JWT `session_id`(UUID)로 Supabase `auth.sessions` 행이 있는지 같은 DB 조회로 본다. 없거나(로그아웃·철회) `session_id`가 없으면 `401 AUTH_INVALID`. 읽기·쓰기 모두 거부, `POST /auth/session`은 토큰 검증만이라 대상 아님. `AUTH_SESSION_CHECK`는 production 필수(local·test 기본 꺼짐, 시험은 대역 `auth.sessions`) |
| §2.5 "A는 M1에 자기 서버 엔드포인트가 없다" | M1 범위에서는 맞다. M2는 §2.6 |

§2.6~§2.11의 M2 행은 전부 `기본값(Claude)`이다(본 레포에 대응 계약이 없다).

상태 낱말(`확정` / `기본값(Claude)` / `미확인(임시)` + Q-번호)은 [05 §0](05_ERD_및_DB설계서.md)과 같다. **주니어(A·B·C) 영역 엔드포인트는 경로·메서드·인증·목적까지만 적는다.** 필드·개수·정렬 세부·화면 동작은 세부 명세서와 계약서의 몫이다.

## 1. 공통 규칙

| 항목 | 값 | 상태 |
| --- | --- | --- |
| 경로 접두어 | `/api/v1` | `확정`(`PROJECT.md` §3) |
| 인증 | `Authorization: Bearer <Supabase access JWT>`. 서버는 JWKS 공개키로 검증하고 자체 토큰을 만들지 않는다 | `확정`(Q-52) |
| 인증 칸의 뜻 | **필수**: `get_current_user`(없으면 401) / **선택**: 토큰이 있으면 내 상태(공감·북마크 여부)를 더하고 없어도 200 / **없음**: 토큰을 보지 않는다 | `기본값(Claude)` |
| 사용자 확정 | 본문·쿼리의 사용자 id는 읽지 않는다. 내 것은 경로에 `/me/`를 쓴다 | `확정`(02 §3) |
| 오류 응답 | `{"error": {"code", "message", "detail"}}` | `확정`(`server/app/common.py`) |
| 날짜·시각 | 날짜는 `YYYY-MM-DD`(서울), 시각은 ISO 8601 초 단위 `+09:00` | `확정`(NFR-03, AUTH-1 §3.1) |
| 목록 넘기기 | 피드·내 목록은 커서(`?cursor=&limit=`), 응답에 `next_cursor`(없으면 `null`). 도서 검색만 제공자에 맞춰 `?start=`(20건씩 "더 보기") | 검색 20건 `확정`(2026-11-13) · 커서 방식 `기본값(Claude)` · `limit` 값 `미확인(임시)` Q-21 |
| 연타·재시도 | 만들기·누르기는 같은 요청을 다시 보내도 한 건이다. 방법은 엔드포인트마다 DB 제약(05 §3.2)으로 흡수하고 두 번째 응답도 성공으로 준다 | `확정`(02 §6) · 방법 `기본값(Claude)` |
| 타인 것·없는 것 | 개인 리소스는 둘 다 `404 NOT_FOUND`로 같다 | `확정`(USR-02) |
| 외부 조회 실패 | **오류가 아니라 200 안의 상태값 `unknown`**이다(소장·대출). 목록 전체를 못 받은 경우만 503 | `확정`(AC-UNKNOWN) |
| 좌표 | 주변 조회는 `lat`·`lng`를 쿼리로 받고 저장·로그하지 않는다 | `확정`(NFR-05) |
| OpenAPI | 꺼져 있다(`openapi_url=None`). 11/19 뒤 검토 | `미확인(임시)`([기준선 §5](기준선.md) 예외 1) |

## 2. 엔드포인트 목록 (M1 — 표 30행)

담당의 괄호는 계약서를 쓰는 Step이다. 조회 엔진(D)의 엔드포인트는 C·A·B의 화면이 부른다.

### 2.1 기반·계정 (D)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 1 | `GET /api/v1/ready` | 없음 | 서버·DB 준비 상태 | — | `확정`(구현됨) |
| 2 | `POST /api/v1/auth/session` | 필수(토큰 검증만, `users` 행 없어도 됨) | 로그인 직후 `users` 행을 만든다(있으면 그대로) | AUTH-01 | `확정`(AUTH-1 계약서 초안) |
| 3 | `GET /api/v1/me` | 필수 | 내 계정(`user_id`·`status`·`created_at`) | AUTH-01 | `확정`(AUTH-1 계약서 초안) |
| 4 | `GET /api/v1/me/settings` | 필수 | 내 주변 반경·반납 집계 동의 읽기 | LIB-02, LOAN-03 | `기본값(Claude)` · 동의 칸 `미확인(임시)` Q-49 |
| 5 | `PATCH /api/v1/me/settings` | 필수 | 위 설정 바꾸기 | LIB-02, LOAN-03 | 같음 |
| 6 | `DELETE /api/v1/me` | 필수 | 탈퇴: 개인 데이터 처리·게시물 철회 | AUTH-03 | `기본값(Claude)` · 처리 범위·보관은 `미확인(임시)` Q-23(AUTH-3 계약서) |

- **로그아웃(AUTH-02)은 서버 엔드포인트가 없다**(`기본값(Claude)`): 앱이 Supabase `signOut()`을 부르고 화면·캐시·기기 예약 알림을 지운다. 철회된 세션의 쓰기 거부는 서버가 JWT의 `session_id`로 확인하는데, 그 방법은 AUTH-2 계약서에서 정한다(AUTH-1 A4). 엔드포인트가 필요해지면 이 표에 더한다.
- 닉네임을 바꾸는 엔드포인트는 두지 않는다(`미확인(임시)` Q-55, 프로필은 요구사항 ID 없음).

### 2.2 조회 엔진 — 도서·도서관·소장 (D가 만들고 C·A·B가 쓴다)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 7 | `GET /api/v1/books/search?q=&start=` | 없음 | 도서 검색(네이버 책 검색), 20건씩 | LIB-01 | `확정` · 응답 필드·한도 `미확인(임시)` Q-41 |
| 8 | `GET /api/v1/books/{isbn13}` | 없음 | 도서 상세(서지·표지 주소) | LIB-01, LOCAL-02 | `확정` · 표지 조건 Q-41 |
| 9 | `GET /api/v1/books/recommendations?library_id=` | 없음 | 검색 진입 화면의 추천: 활성 테마가 있으면 테마, 없으면 인기 도서. `library_id`가 있으면 그 도서관, 없으면 전국. 응답에 기준 문구 | LIB-01(C-46 E1~E3) | 동작 `확정` · M1은 테마 표가 없어 항상 인기 도서(`기본값(Claude)`) · API 선택 `미확인(임시)` Q-42 |
| 10 | `GET /api/v1/libraries?lat=&lng=&radius_km=` 또는 `?dtl_region=` | 없음 | 주변(반경 3 또는 5km, 거리순) 또는 시군구의 도서관 목록. 지도 핀·"내 주변 도서관"·위치 거부 때 목록이 같은 엔드포인트를 쓴다 | LIB-02, VISIT-01 | `확정`(2026-11-13: 직선거리, 핀과 목록에 같은 반경) · 지도에 반경 밖 도서관을 보일지 `미확인(임시)` Q-51 |
| 11 | `GET /api/v1/libraries/{library_id}` | 없음 | 도서관 하나(방문 페이지 헤더: 이름·오늘 운영시간·휴관 원문과 계산 결과) | VISIT-02, LIB-02 | `확정`(Q-22) |
| 12 | `GET /api/v1/books/{isbn13}/availability?scope=nearby&lat=&lng=&radius_km=` | 없음 | 주변 도서관별 소장·대출 가능(세 갈래)·출처·조회 시각·데이터 기준일·"실시간 확인" 주소 | LIB-03·04·06·07 | `확정` · 기준일 필드 `미확인(임시)` Q-18 · 주소 규칙 `미확인(임시)` Q-48 |
| 13 | `GET /api/v1/books/{isbn13}/availability?scope=city&dtl_region=` | 없음 | "현재 도시 내 모든 도서관" 재검색. 응답한 곳만 보여 주고 나머지는 `unknown` | LIB-07 | `확정`(도시 = 시군구, 2026-11-13) · 호출량은 실측 `미확인(임시)` Q-18 |
| 14 | `GET /api/v1/books/{isbn13}/availability?library_id=` | 없음 | 도서관 하나의 소장·대출 가능(게시물 상세의 대여 경로, 방문 중인 도서관 우선) | LIB-03, LOCAL-04 | `확정` |
| 15 | `GET /api/v1/books/{isbn13}/purchase-link` | 없음 | 예스24 구매 주소 | LOCAL-04 | `미확인(임시)` Q-41 ②(링크 생성 방식·약관). 풀리기 전에는 예스24 검색 주소로 보내는 기본 연결만 |

- 12~14는 경로가 같고 `scope`·`library_id`로 나뉜다(하나의 핸들러). 늦은 응답 폐기(LIB-04, AC-RACE)는 서버가 아니라 앱이 요청 세대로 처리한다(`기본값(Claude)`).
- 호출 상한(정보나루 일 21,000건)을 넘으면 새로 부르지 않고 캐시에 있는 것만 주며 나머지는 `unknown`으로 표시한다. 전부 막혔을 때만 `429 PROVIDER_LIMIT`(`기본값(Claude)`).
- 지역 이름으로 보는 위치를 옮기는 검색(`library-visit` 결정 13)은 서버 엔드포인트를 두지 않고 앱에 넣은 시군구 코드 표에서 찾는다(`기본값(Claude)`, 정보나루 지역 코드는 고정 목록).

### 2.3 빌릴 예정·반납 비서 (C)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 16 | `GET /api/v1/me/loan-plans` | 필수 | 내 빌릴 예정 목록 | LIB-05 | `확정` |
| 17 | `POST /api/v1/me/loan-plans` | 필수 | 책 + 도서관으로 예정 저장(같은 조합은 한 건) | LIB-05, AC-PLAN | `확정` |
| 18 | `DELETE /api/v1/me/loan-plans/{plan_id}` | 필수 | 예정 해제(상태를 `released`로) | LIB-05 | `확정` · 행을 지울지 상태만 바꿀지는 `기본값(Claude)`(상태) |
| 19 | `GET /api/v1/me/loans?status=` | 필수 | 내 대출(대출 중·지난 대출). D-day·연체는 서버가 계산해 준다. 앱은 이 목록으로 기기 알림을 맞춘다 | LOAN-01·05, AC-NOTIFY | `확정` |
| 20 | `POST /api/v1/me/loans` | 필수 | "빌렸어요": 대출일 = 서버 서울 오늘, 예정일 = +14일(추정). 예정에서 왔으면 연결 | LOAN-01, AC-LOAN·AC-DATE | `확정` · 같은 책 중복 기준 `미확인(임시)` Q-21 |
| 21 | `PATCH /api/v1/me/loans/{loan_id}` | 필수 | 반납 예정일 고치기(대출일 이전 불가) | LOAN-02 | `확정` |
| 22 | `POST /api/v1/me/loans/{loan_id}/return` | 필수 | "반납했어요". 동의했고 도서관이 있으면 반납 집계 +1 | LOAN-03, AC-RETURN | `확정` · 집계 쓰기는 `미확인(임시)` Q-49(LOAN-2 계약서에서 켠다) |

기기 예약 알림(LOAN-04·05)은 서버 엔드포인트가 없다(앱이 19의 목록으로 예약한다). 알림 시각은 `미확인(임시)` Q-19.

### 2.4 지역 SNS (B)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 23 | `POST /api/v1/uploads/post-images` | 필수 | 직접 찍은 사진 올리기. 서버가 EXIF 위치를 지우고 저장 경로를 돌려준다 | LOCAL-01, NFR-05 | 동작 `확정` · 저장소·용량·형식 `미확인(임시)` Q-53 |
| 24 | `POST /api/v1/posts` | 필수 | 올리기(이때 공개된다). 이미지 종류 사진/표지/단색, 본문 없이도 됨 | LOCAL-01·02, AC-PUBLISH | `확정` |
| 25 | `POST /api/v1/posts/{post_id}/withdraw` | 필수(작성자만) | 철회. 바로 목록·직접 주소에서 안 보인다 | LOCAL-01, R10 | `확정` |
| 26 | `GET /api/v1/libraries/{library_id}/posts?sort=latest&cursor=` | 선택 | 그 도서관 광장 피드(공개 게시물만) | LOCAL-03, VISIT-02 | 최신순 `확정` · `sort=popular`는 `미확인(임시)` Q-31(기준이 정해질 때까지 열지 않는다) · 파일럿 공개 범위 `미확인(임시)` Q-54 |
| 27 | `GET /api/v1/posts/{post_id}` | 선택 | 게시물 상세(본문·작성자 닉네임·공감 수·내 공감·내 북마크·책) | LOCAL-04 | `확정` · 철회·숨김은 `404 POST_NOT_AVAILABLE` |
| 28 | `GET /api/v1/books/{isbn13}/posts?exclude=&cursor=` | 선택 | 같은 책의 다른 공개 게시물(다른 도서관 포함) | LOCAL-05 | `확정` |
| 29 | `PUT /api/v1/posts/{post_id}/reaction` · `DELETE …/reaction` | 필수 | 공감 누르기·취소(몇 번 눌러도 결과 같음) | LOCAL-06, R14 | `확정` |
| 30 | `PUT /api/v1/posts/{post_id}/bookmark` · `DELETE …/bookmark` | 필수 | 북마크 저장·해제 | LOCAL-03 | `미확인(임시)` Q-56 |

- 12~14는 한 경로이고 29·30은 각각 메서드가 둘(`PUT`·`DELETE`)이다. 메서드·경로 쌍으로 세면 30개다.
- 내 게시물 목록·북마크 모음·좋아요 모음을 읽는 엔드포인트는 **두지 않는다**(프로필 3탭은 요구사항 ID 없음, [기준선 §7](기준선.md)). 철회는 상세 화면에서 한다.
- 상세가 "펼쳐지고 주변에 피드가 이어지는" 것은 26·28을 다시 부르는 것으로 하고 전용 엔드포인트를 두지 않는다(`기본값(Claude)`).
- 공유 링크(C-46 D2)의 주소 모양은 딥링크와 얽혀 LOCAL-2 계약서에서 정한다.

### 2.5 도서관 방문 (A — M1)

A는 M1에 자기 서버 엔드포인트가 없다. 지도 홈은 10번, 방문 페이지 헤더는 11번, 피드 자리는 26번을 쓴다. 도서관 기본값·보는 위치·방문 횟수는 기기에만 둔다(05 §6).

---

### 2.6 도서관 방문 M2 확장 — 방명록·오늘의 서가·스탬프·홈 하단 (`VISIT-3`, `VISIT-4`)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 |
| :---: | :--- | :--- | :--- | :--- |
| 31 | `GET /api/v1/libraries/{library_id}/guestbook?cursor=` | 선택 | 해당 도서관 공개 방명록 목록 (피드 혼합용 및 단독 조회) | VISIT-03 |
| 32 | `POST /api/v1/libraries/{library_id}/guestbook` | 필수 | 도서관 방명록 짧은 글 작성 | VISIT-03 |
| 33 | `DELETE /api/v1/guestbook/{entry_id}` | 필수(작성자) | 본인 방명록 글 삭제(`status='deleted'`) | VISIT-03 |
| 34 | `GET /api/v1/libraries/{library_id}/bookshelf` | 없음 | 방문 페이지 하단 "오늘의 서가" 3종(① 요즘 읽은 책 반납 집계 ② 도서관 인기 도서 ③ 운영자 테마 추천 도서, 페이지당 3권 단위) | VISIT-04 |
| 35 | `GET /api/v1/libraries/{library_id}/visit-stamp/today` | 필수 | 오늘(서울 날짜) 해당 도서관 방문 스탬프 상태 조회 | VISIT-05 |
| 36 | `POST /api/v1/libraries/{library_id}/visit-stamp` | 필수 | 오늘의 "다녀왔어요" 스탬프 찍기 및 공개 여부(`is_public`) 설정/변경 | VISIT-05 |
| 37 | `GET /api/v1/home/summary?lat=&lng=` | 선택 | 지도 홈 하단 섹션: 지역 인기글·내 최근 독서 기록(로그인 시)·추천 서적 | VISIT-06 |

### 2.7 비공개 독서 기록 & 내 발자취 (`READ-1`, `READ-2`)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 |
| :---: | :--- | :--- | :--- | :--- |
| 38 | `GET /api/v1/me/reading-logs?library_id=&cursor=` | 필수 | 내 비공개 독서 기록 전체 또는 도서관별 필터(내 발자취) 조회 | READ-01, READ-02 |
| 39 | `POST /api/v1/me/reading-logs` | 필수 | 비공개 독서 기록 작성 (도서관 미선택 시 `library_id = null` 그대로 저장) | READ-01 |
| 40 | `PATCH /api/v1/me/reading-logs/{log_id}` | 필수 | 내 독서 기록 수정 | READ-01 |
| 41 | `DELETE /api/v1/me/reading-logs/{log_id}` | 필수 | 내 독서 기록 삭제 | READ-01 |
| 42 | `GET /api/v1/me/reading-logs/stats` | 필수 | 독서 기록 기초 통계(전체 권수·이번 달 권수·방문 기록 도서관 수, 빈 값은 `0`) | READ-02 |

### 2.8 도서관 기반 작은 모임 (`CLUB-1`, `CLUB-2`, `CLUB-03`)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 |
| :---: | :--- | :--- | :--- | :--- |
| 43 | `GET /api/v1/libraries/{library_id}/clubs?cursor=` | 선택 | 해당 도서관의 작은 모임 목록 | CLUB-01 |
| 44 | `POST /api/v1/libraries/{library_id}/clubs` | 필수 | 새 모임 만들기 (시간·장소 미정 허용, 정원 선택) | CLUB-01 |
| 45 | `GET /api/v1/clubs/{club_id}` | 선택 | 모임 상세 (일정·장소·정원·참가자 수·내 참가 상태·연결된 다음 회차 모임 목록) | CLUB-01, CLUB-02 |
| 46 | `PATCH /api/v1/clubs/{club_id}` | 필수(생성자) | 일정·장소 확정/변경(시작 후 시작 시각 변경 금지), 조기 모집 마감(`status='closed'`) — 참가자에게 알림 생성 | CLUB-01 |
| 47 | `POST /api/v1/clubs/{club_id}/cancel` | 필수(생성자) | 종료 전 모임 취소 (`cancel_reason` 필수, 참가자 알림 생성) | CLUB-01 |
| 48 | `POST /api/v1/clubs/{club_id}/join` · `DELETE .../join` | 필수 | 즉시 참가 신청(승인 없음, 패널티 기간 중이면 `403 PENALTY_RESTRICTED`) 및 시작 전 참가 취소 | CLUB-01, CLUB-03 |
| 49 | `POST /api/v1/clubs/{club_id}/attendance` | 필수 | 종료된 모임에서 본인 참석 체크(`self_attended`) 또는 만든 사람의 참가자 출석/불참(`attended`/`no_show`) 표시. **`no_show`는 패널티를 바로 만들지 않고 운영자 확인 대기열(#62)에 올린다**(02 §3 "자동 부과하지 않는다", 02 §9). 취소된 모임은 `409 CONFLICT` | CLUB-02, CLUB-03 |
| 50 | `GET /api/v1/clubs/{club_id}/comments` · `POST .../comments` | 선택 / 필수 | 모임 장소·시간 협의 댓글 조회 및 작성(패널티 제한 시 `403 PENALTY_RESTRICTED`) | CLUB-01, CLUB-03 |
| 51 | `DELETE /api/v1/club-comments/{comment_id}` | 필수(작성자) | 본인 댓글 삭제 | CLUB-01 |
| 52 | `POST /api/v1/club-comments/{comment_id}/delete-request` | 필수(모임 생성자) | 만든 사람의 특정 댓글 삭제 및 참가 제한 요청 접수(중복 방지, 관리자 승인 전 댓글 유지) | CLUB-01, CLUB-03 |
| 53 | `GET /api/v1/clubs/{club_id}/my-review` · `PUT .../my-review` | 필수 | 모임 종료 후 본인 비공개 후기 조회·작성·수정 (선택적으로 공개 SNS 게시물로 별도 발행) | CLUB-02 |
| 54 | `POST /api/v1/clubs/{club_id}/next-club` | 필수(참가자) | 이전 회차 정보를 복사해 다음 회차 모임 생성 및 이전 참가자(취소·제한자 제외)에게 알림 발송 | CLUB-02 |

### 2.9 프로필 3탭·이웃 팔로우·통합 북마크·알림함 (`AUTH-4` / `USR-03~06`)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 |
| :---: | :--- | :--- | :--- | :--- |
| 55 | `GET /api/v1/me/profile` · `PATCH /api/v1/me/profile` | 필수 | 내 프로필(닉네임·한 줄 소개·아바타) 조회 및 편집 | USR-03 |
| 56 | `GET /api/v1/users/{user_id}/profile` | 선택 | 타 사용자 공개 프로필(닉네임·소개·내 팔로우 여부·공개 게시물 목록, 팔로워 수/목록 비노출) | USR-03, USR-04 |
| 57 | `PUT /api/v1/users/{user_id}/follow` · `DELETE .../follow` | 필수 | 이웃 팔로우 및 언팔로우 (멱등) | USR-04 |
| 58 | `GET /api/v1/me/collections/{tab}?library_id=&cursor=` | 필수 | 내 정보 3탭 조회: `tab` = `posts`(내 게시물) / `likes`(좋아요 모음, 최근순) / `bookmarks`(북마크 모음, 최근순, 철회·숨김 제외) | USR-03, USR-05 |
| 59 | `PUT /api/v1/bookmarks/{target_type}/{target_id}` · `DELETE ...` | 필수 | 통합 북마크 저장·해제 (`target_type`: `post`, `guestbook`, `club`, `stamp`, 재저장 시 맨 앞) | USR-05, LOCAL-03 |
| 60 | `GET /api/v1/me/notifications?cursor=` · `POST .../read` | 필수 | 앱 내 알림함 목록(안 읽은 수 포함) 조회 및 개별/전체 읽음 처리 | USR-06 |

### 2.10 신고·운영자 숨김·테마/룩/패널티 관리 (`LOCAL-4`, `VISIT-4`, `CLUB-03`)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 |
| :---: | :--- | :--- | :--- | :--- |
| 61 | `POST /api/v1/reports` | 필수 | 게시물·방명록·모임·모임 댓글 신고 접수(`target_type`: `post`/`guestbook`/`club`/`club_comment`). 같은 사람이 같은 대상을 다시 신고하면 한 건(성공 응답) | LOCAL-08 |
| 62 | `GET /api/v1/admin/reports?kind=&cursor=` · `POST /api/v1/admin/reports/{id}/resolve` | 필수(운영자) | 운영 대기열 조회와 처리. `kind`: `report`(신고) / `comment_delete`(#52 요청) / `no_show`(#49 표시) / `appeal`(#69 재검토). 처리: 숨김·기각 / 댓글 삭제만·삭제와 제한 / 불참 확정(패널티 생성)·기각 / 패널티 해제·유지. 처리 사유(`admin_note`)는 필수이고 대상자에게 알림함으로 안내. 응답에 신고자 id·타인 비공개 데이터 없음 | LOCAL-08, CLUB-03 |
| 63 | `PATCH /api/v1/admin/libraries/{library_id}/look` | 필수(운영자) | 도서관 룩 지정·재배정(`look_is_manual = true`) | VISIT-07 |
| 64 | `GET /api/v1/admin/shelf-themes` · `POST /api/v1/admin/shelf-themes` · `PATCH /api/v1/admin/shelf-themes/{theme_id}` | 필수(운영자) | 서가 테마(범위·기간·활성·도서 목록과 순서) 조회·생성·수정 | VISIT-04, LIB-01 |
| 65 | `POST /api/v1/admin/penalties/{penalty_id}/release` | 필수(운영자) | 재검토 요청과 무관하게 패널티 직접 해제(`active = false`), 사유 필수 | CLUB-03 |

### 2.11 02 요구사항에 대응 엔드포인트가 없어 더한 것 (2026-11-15 문서 리뷰, `DEF-011`)

| # | 메서드·경로 | 인증 | 목적 | 요구사항 | Step |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 66 | `GET /api/v1/libraries/{library_id}/feed?kinds=&sort=&bookmarked=&cursor=` | 선택 | **혼합 광장 피드**: 게시물·방명록·모임·공개 방문 스탬프를 같은 카드 모양(`kind` + 공통 필드 + 종류별 필드)으로 한 커서에 섞어 준다. 정렬 키는 각 종류의 공개 시각, `sort=popular`는 게시물의 `like_count`만 반영(나머지는 0). `bookmarked=true`(필수 인증)는 현재 도서관 북마크 필터. #26(게시물만)은 M1 호환 경로로 그대로 둔다 | LOCAL-03, VISIT-03·05, CLUB-01, USR-05 | VISIT-3(게시물+방명록) → VISIT-4(`stamp`) → CLUB-1(`club`) |
| 67 | `GET /api/v1/me/visit-stamps?library_id=&cursor=` | 필수 | 내 방문 스탬프 수집함(본인만) | VISIT-05, AC-STAMP | VISIT-4 |
| 68 | `GET /api/v1/me/following/posts?cursor=` | 필수 | 팔로우한 이웃의 공개 게시물 모아 보기(최신순). 팔로우 목록 자체는 응답에 없다 | USR-04 | AUTH-4 |
| 69 | `GET /api/v1/me/penalties` · `POST /api/v1/me/penalties/{penalty_id}/appeal` | 필수 | 내 제한(종류·사유·만료 시각) 조회와 재검토 요청(건당 한 번, 대기 중 재요청은 같은 응답) | CLUB-03 | LOCAL-4 |
| 70 | `GET /api/v1/me/clubs?role=&cursor=` | 필수 | 내가 만든·참가한 모임 기록(날짜·장소·책·내 참가/참석 여부·후기 유무, 다음 회차 연결) | CLUB-02(C-46 C1) | CLUB-2 |
| 71 | `GET /api/v1/uploads/files/{filename}` | 없음 | 개발·시연 환경의 업로드 파일 정적 서빙(Q-53). 파일 이름은 서버가 만든 무작위 이름만 허용(경로 문자 거부), `production`에서는 저장소 URL로 대체 | LOCAL-01 | LOCAL-1 |
| 72 | `POST /api/v1/uploads/avatars` | 필수 | 프로필 사진 올리기(#23과 같은 EXIF 제거·형식·용량 규칙) | USR-03 | AUTH-4 |

- 최근 본 도서는 기기에 두므로 엔드포인트가 없다(02 §9).
- 모임의 시작·종료에 따른 상태(`closed`·`completed`)는 배치 없이 읽을 때 파생한다(02 §9 "모임 상태 전이").

## 3. 공통 오류 코드

기능별 오류(예: 날짜 역전)는 계약서 §4에서 이 표의 코드를 쓰고, 표에 없는 코드가 필요하면 이 표에 먼저 더한다.

| 코드 | HTTP | 언제 | 화면 문구(기본) | DB | 상태 |
| --- | --- | --- | --- | --- | --- |
| `AUTH_REQUIRED` | 401 | `Authorization` 헤더 없음·형식 다름 | "로그인이 필요해요." | 무변경 | `확정`(AUTH-1 초안) |
| `AUTH_INVALID` | 401 | 서명·발급자·대상·역할·형식 불일치, 로그아웃·철회된 세션(`DEF-008`) | "로그인 정보를 확인하지 못했어요. 다시 로그인해 주세요." | 무변경 | `확정`(AUTH-1 초안) |
| `AUTH_EXPIRED` | 401 | 토큰 만료 | 문구 없이 갱신 뒤 한 번 재시도 | 무변경 | `확정`(AUTH-1 초안) |
| `AUTH_NOT_REGISTERED` | 401 | 토큰은 맞지만 `users` 행 없음 | 문구 없이 `POST /auth/session` 뒤 한 번 재시도 | 무변경 | `확정`(AUTH-1 초안) |
| `ACCOUNT_WITHDRAWN` | 403 | 탈퇴한 계정 | "탈퇴한 계정이에요." | 무변경 | `기본값(Claude)`(AUTH-3이 다시 봄) |
| `AUTH_UNAVAILABLE` | 503 | JWKS를 받지 못함 | "로그인 확인이 잠시 안 돼요. 잠시 뒤 다시 시도해 주세요." | 무변경 | `확정`(AUTH-1 초안) |
| `PENALTY_RESTRICTED` | 403 | 패널티 기간 중의 모임 참가(#48)·제한 범위 안의 댓글 작성(#50). `detail`에 종류·만료 시각(영구면 `null`) | "지금은 참가할 수 없어요."(사유·만료 시각을 함께 보인다) | 무변경 | `기본값(Claude)`(CLUB-03) |
| `FORBIDDEN` | 403 | 로그인은 했지만 할 수 없는 일(남의 게시물 철회 등 **공개** 리소스, 운영자가 아닌 계정의 `/admin/*`) | "할 수 없는 요청이에요." | 무변경 | `기본값(Claude)` |
| `NOT_FOUND` | 404 | 없는 경로, 없는 것, **타인 소유의 개인 리소스**(둘을 구분하지 않음) | "찾을 수 없어요." | 무변경 | `확정`(구현됨, USR-02) |
| `POST_NOT_AVAILABLE` | 404 | 철회·운영 숨김·삭제된 게시물 | "더 이상 공개되지 않는 게시물이에요." | 무변경 | `기본값(Claude)`(02 §6) |
| `METHOD_NOT_ALLOWED` | 405 | 허용되지 않는 메서드 | "허용되지 않는 요청 방식이에요." | 무변경 | `확정`(구현됨) |
| `CONFLICT` | 409 | 지금 상태에서 할 수 없는 변경(이미 반납한 대출의 예정일 수정, 정원이 찼거나 모집이 마감·취소된 모임 참가, 시작한 모임의 참가 취소·시작 시각 변경 등) | "이미 바뀐 내용이에요. 새로 고친 뒤 다시 시도해 주세요." | 무변경 | `기본값(Claude)`(02 §6 "충돌 안내 후 재조회") |
| `VALIDATION_ERROR` | 422 | 필수값 누락·형식 오류·날짜 역전·잘못된 ISBN. `detail`에 필드 이름 | "요청 형식이 올바르지 않아요."(화면은 필드별 문구로 바꿔 보인다) | 무변경 | `확정`(구현됨) |
| `PAYLOAD_TOO_LARGE` | 413 | 사진이 용량 상한을 넘음 | "사진이 너무 커요." | 무변경 | `미확인(임시)` Q-53(상한 값) |
| `PROVIDER_LIMIT` | 429 | 외부 호출 상한에 걸려 줄 것이 하나도 없음 | "지금은 조회가 많아요. 잠시 뒤 다시 시도해 주세요." | 무변경 | `기본값(Claude)` |
| `PROVIDER_UNAVAILABLE` | 503 | 목록 자체를 못 받음(도서 검색·도서관 목록). 소장·대출의 일부 실패는 오류가 아니라 `unknown` | "정보를 가져오지 못했어요. 다시 시도해 주세요." | 무변경 | `기본값(Claude)`(AC-UNKNOWN) |
| `DB_TIMEOUT` · `DB_UNAVAILABLE` | 503 | DB 응답 지연·연결 실패 | "데이터베이스에 연결하지 못했어요." | 무변경(트랜잭션 롤백) | `확정`(구현됨) |
| `INTERNAL_ERROR` | 500 | 예상하지 못한 오류 | "문제가 생겼어요." | 무변경(롤백) | `확정`(구현됨) |

- 연타·재시도로 같은 것을 다시 만들려는 요청은 **오류가 아니라 성공**으로 답한다(§1).
- 화면 문구의 `기본값(Claude)`은 세부 명세서가 화면에 맞게 다시 정할 수 있다. 코드와 HTTP 상태는 바꾸지 않는다.

## 4. 화면 ↔ 엔드포인트 (M1 여정)

| 여정(유저 플로우) | 화면 | 엔드포인트 | 담당 |
| --- | --- | --- | --- |
| §2 방문 | 지도 홈 → 핀 → 방문 페이지 | 10 → 11 + 26 | A(화면), D(10·11), B(26) |
| §3 책 확인 | 검색 진입 → 결과 → 상세 → 소장 조회 → 도시 재검색 | 9 → 7 → 8 → 12 → 13 | C(화면), D |
| §3 빌릴 예정 | 소장 조회 결과 → 담기 → 내 예정 | 17 → 16, 18 | C |
| §4 반납 비서 | 빌렸어요 → D-day → 예정일 수정 → 반납했어요 | 20 → 19 → 21 → 22 | C |
| §5 게시물 | 글쓰기 → 올리기 → 철회 | (23) → 24 → 25 | B |
| §1 순환 | 피드 → 상세 → 대여(소장 조회)·구매·이어 읽기·공감 | 26 → 27 → 14 · 15 · 28 · 29 | B(화면), D(14·15) |
| §7 계정 | 로그인 → 로그아웃 → 탈퇴 | 2 → (서버 없음) → 6 | D |

## 5. 아직 쓰지 않은 것

- **단독 예비본 규칙**: 계약서가 없으므로 각 Step은 구현한 엔드포인트의 요청·응답 필드 표(이름·타입·필수·예시 1건)를 **같은 Step 커밋에서 이 문서 §7 이하에 더한다**(`H-DOC-01`). 필드 표가 없는 엔드포인트는 리뷰에서 S2다.

- 요청·응답 필드 표와 실제 호출 예시: 계약서가 정하고 구현 뒤 여기에 옮긴다.
- 플랫폼 분기 표 취합(계약서 §3.3): 지금은 AUTH-1 초안의 5행뿐이라 계약서를 가리킨다.
- OpenAPI: 꺼져 있다(§1).

## 6. 미확인 모음 (이 문서에서 임시로 둔 것)

Q-18(기준일·호출량), Q-19(알림 시각), Q-21(`limit`·중복 대출), Q-23(탈퇴 처리 범위), Q-31(인기순), Q-41(네이버·예스24 조건), Q-42(인기 도서 API), Q-48(실시간 확인 주소), Q-49(반납 집계), Q-51(지도에 보일 도서관 범위), Q-53(사진 저장소), Q-54(파일럿 공개 범위), Q-55(닉네임), Q-56(북마크). 내용은 [모호점 해소 기록](모호점_해소_기록.md)과 [05 §11](05_ERD_및_DB설계서.md).

단독 예비본에서의 처리는 위 Q 전부에 대해 [05 §11](05_ERD_및_DB설계서.md)(DB·외부 API·저장소)과 [02 §9](02_요구사항_정의서.md)(동작·수치)에 있다.

## 7. 구현된 엔드포인트의 요청·응답 (Step마다 더한다)

| # | Step | 요청 | 응답(200) | 비고 |
| :---: | :--- | :--- | :--- | :--- |
| 2 | AUTH-1-P3, AUTH-2-3 | 본문 없음(보내도 읽지 않음 — `user_id`를 보내도 무시) | `user_id`(str, UUID = 토큰 `sub`), `status`(`"active"`), `is_new`(bool, 이번 요청이 `users` 행을 만들었으면 `true`), `created_at`(str, `users.created_at`, ISO 8601 초 `+09:00`) | 인증은 토큰 검증만(`users` 행·세션 행 불필요). 활성 계정이면 같은 트랜잭션에서 `user_profiles`(닉네임 `이웃-<sub 앞 4자>`)를 없을 때만 만든다(하네스 §7 편차 3). 오류: 401 `AUTH_REQUIRED`·`AUTH_INVALID`·`AUTH_EXPIRED`, 403 `ACCOUNT_WITHDRAWN`, 503 `AUTH_UNAVAILABLE`·`DB_UNAVAILABLE` |
| 3 | AUTH-1-P3 | — | `user_id`, `status`, `created_at`(#2와 같음, `is_new` 없음) | 오류: #2 + 401 `AUTH_NOT_REGISTERED` |
| 4 | AUTH-2-3 | — | `nearby_radius_km`(int, `3`\|`5`), `return_stats_consent`(bool), `return_stats_consent_at`(str \| `null`, 처음 동의한 시각 `+09:00`), `updated_at`(str \| `null`) | `user_settings` 행이 없으면 DB에 쓰지 않고 `{3, false, null, null}`. `return_stats_consent`는 `return_stats_consent_at IS NOT NULL`에서 파생(`DEF-006`) |
| 5 | AUTH-2-3 | JSON `{"nearby_radius_km"?: 3\|5, "return_stats_consent"?: bool}` — 둘 중 하나 이상(`null`은 보내지 않은 것과 같음). 정수·불리언 엄격(`"5"`·`true`를 반경으로 받지 않음), 모르는 필드 거부 | #4와 같은 4필드 | 보내지 않은 칸은 그대로(동시 요청도 서로 덮지 않음, `DEF-013`). 이미 동의한 상태의 재동의는 처음 시각 유지, `false`는 시각을 `null`로. 오류: 422 `VALIDATION_ERROR`(`detail`은 필드 이름, 여럿이면 쉼표 — 예: `"nearby_radius_km"`, 빈 본문은 `"nearby_radius_km,return_stats_consent"`, `DEF-016`) |
| 6 | AUTH-2-3 | 본문 없음 | `user_id`(str), `status`(`"withdrawn"`), `withdrawn_at`(str, 처리 시각 `+09:00` — 응답에만 있고 저장 칸은 없다) | 한 트랜잭션에서 05 §11.1 표대로 처리. 이미 탈퇴했거나 동시에 들어온 두 번째 탈퇴는 403 `ACCOUNT_WITHDRAWN`(`DEF-014`) |

- #3~#6 공통(`get_current_user`): `AUTH_SESSION_CHECK=true`(production 필수)이면 로그아웃·철회된 세션이나 `session_id`가 없는 토큰은 401 `AUTH_INVALID`(`DEF-008`). 쓰기(#5·#6)는 트랜잭션 첫 SQL에서 계정을 다시 잠가 확인한다(`DEF-014`).
- 예시(#5): 요청 `{"nearby_radius_km": 5, "return_stats_consent": true}` → `200 {"nearby_radius_km": 5, "return_stats_consent": true, "return_stats_consent_at": "2026-11-15T10:00:00+09:00", "updated_at": "2026-11-15T10:00:00+09:00"}`
- 대조 근거: `server/app/auth.py`(`create_session`·`get_me`·`get_current_user`), `server/app/routers/me.py`, `server/app/main.py`(검증 오류 처리기), 시험 `test_auth_session.py`·`test_me.py`·`test_me_concurrency.py`·`test_auth_revoked_session.py` (Phase 1 코드 리뷰 2026-11-15)

