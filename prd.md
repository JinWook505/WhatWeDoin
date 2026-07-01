# 제품 요구사항 명세서 (PRD) — WhatWeDoin MVP

| 항목 | 내용 |
|---|---|
| 문서 버전 | **v2.7** — PRD |
| 작성일 | 2026-07-01 |
| 관련 문서 | 없음  |
| 범위 | 제품 개요 / 사용자 플로우 / 기능요구(User Story·인수조건) / 비기능요구 / 기술스택 / DB / API / 인증 / 추천엔진 / 보안 / 설정값 |
| 상태 | MVP 확정. 단일 질의어(자연어) 입력 기반 추천으로 개편(역 수동 선택 UI 제거), 코스는 단계별 복수 대안 구조로 생성 |

### 변경 이력
| 버전 | 일자 | 변경 |
|---|---|---|
| v2.7 | 2026-07-01 | **코스 생성을 "고정 선형 동선" → "단계(stage)별 복수 대안" 구조로 개편(D-26).** ① 실제 데이트/모임 코스는 식사를 2번, 카페를 2번 가는 식으로 딱딱하게 짜이지 않는다는 사용자 피드백 반영 — 코스를 2~4개의 "단계"(예: 저녁 식사, 카페/디저트, 야외 산책)로 구성하고 각 단계마다 1~3개의 대안 장소를 제시, 사용자가 각 단계에서 하나씩 골라 자신만의 동선을 완성. ② LLM 코스 생성 프롬프트가 현재 날씨(맑음/비 등)를 반영해 우천 시 실내 위주 단계로, 맑을 때는 야외 단계(공원 산책 등)를 포함하도록 구성. ③ `course_places` 스키마: `visit_order` → `stage_order` + `option_index` + `stage_label`, `walking_distance_to_next_km` → `walking_distance_from_station_km`(단계 내 대안들은 병렬 관계라 "다음 장소까지 거리" 개념이 성립하지 않음). ④ `POST /v1/courses/recommend`·`GET /v1/courses/{id}` 응답의 `places[]` 배열 → `stages[].options[]` 구조로 변경. ⑤ `content_hash`는 place_id 정렬 목록이 아니라 단계+옵션 전체 구조를 해시. |
| v2.6 | 2026-07-01 | **초기 입력을 "역 선택 + 질의어" → "질의어 단일 입력"으로 전면 개편(D-20).** ① 최초 화면의 지도/역 이름 검색 UI 제거 — 사용자는 "어떻게 놀고 싶은지" 한 문장만 입력. ② 질의어 안의 지명·동네 언급을 LLM이 추출해 최근접 지원 역으로 자동 매핑(`station_name` → `station_id` resolution), GPS는 계속 미사용(D-20은 D-1 위치 정책 유지, 수집 방식만 변경). ③ 지명이 전혀 언급되지 않거나 분류가 불충분하면 **US-A4(추가 입력 요청 Step)** 로 보완 — 기존 SCRUM-60 "PRD 비정합" 플래그를 본 버전에서 공식 해소하고 `missing_fields`에 `station_id`를 포함하도록 확장. ④ US-A1(지도 선택)·US-A2(역 이름 검색)는 메인 화면 1차 진입점에서 **US-A4 폴백 전용**으로 격하(P0→P1). ⑤ `POST /v1/courses/recommend` 요청에서 `station_id`는 선택값으로 전환(질의어에서 해석 실패 시에만 클라이언트가 값 채움). ⑥ `GET /v1/recommend/placeholder`는 `station_id` 없이도 동작(서울 기본 좌표 날씨로 폴백). |
| v2.5 | 2026-06-30 | **SCRUM-70 법무 게이트 범위 확정 + 사용자 제보 MVP 정책 수정.** ① SCRUM-70 범위 확정: 카카오 로컬 REST API 기본 메타(이름·주소·카테고리·좌표·전화번호) 사용은 이용약관 허용 범위 → 법무 게이트 대상은 **크롤링(상세 페이지 스크래핑)에 한함**. ② `business_hours`(영업시간)·`place_rating`(별점)은 카카오 API 미제공 → MVP에서 **사용자 직접 입력으로 수집**(playwright 검증 없는 단순 제보). ③ `places` 테이블에 `user_rating_sum`·`user_rating_count` 컬럼 추가. ④ `POST /v1/places/{place_id}/report` 엔드포인트 추가(영업시간·별점·가격 사용자 제보). ⑤ Out 섹션에서 "영업시간 제보 로직" 표현 수정: 단순 사용자 입력은 MVP 포함, playwright 검증 파이프라인만 V2 유지. |
| v2.4 | 2026-06-29 | **카카오 API 한계 반영 및 LLM 전략 수정.** ① `places` 테이블에 `theme_tags` 컬럼 추가(카카오 API 미제공 → ETL 시 카테고리 코드→enum 매핑으로 채움). ② 카카오 API 평점·영업시간 미제공 정책 명시(영업시간 크롤링 불가 → 사용자 제보만 허용). ③ `LLM_MODEL_PRIMARY`: `claude-opus-4-8` → `claude-sonnet-4-6`(비용 최적화). ④ LLM Provider 추상화 인터페이스 설계 추가(OpenAI 등 타 공급자 전환 대비). ⑤ `station_lines` 테이블 시딩 필요 명시. ⑥ `stations` 시딩 upsert 정책 명시 + 지방 도시(대구·부산 등) 확장 고려. ⑦ **플레이스 단위 리뷰·영업시간 제보 로직(playwright·소형모델·보상체계) → V2 명시** (Out 섹션 추가). |
| v2.3 | 2026-06-25 | **인프라 간소화.** Redis/ElastiCache·S3+CloudFront 제거. 캐시·레이트리밋·refresh 토큰·날씨 캐시 모두 PostgreSQL로 처리. AWS 인프라: ECS + RDS + ALB 유지. 프론트는 Vercel(또는 정적 호스팅). DB 스키마 관리: Alembic 유지. |
| v2.2 | 2026-06-25 | **백엔드 스택 변경.** Java 21 + Spring Boot → **Python 3.12 + FastAPI**. Langfuse Python SDK 네이티브 지원이 주된 이유. SQLAlchemy 2.x(async) + asyncpg, Alembic(마이그레이션), uv(패키지 관리), prometheus-fastapi-instrumentator(메트릭). `/actuator/health` → `GET /health`. |
| v2.1 | 2026-06-25 | **미해결 결정 해소.** ① `rating.prior_mean=50`(중립값, D-18). ② `theme_tag` enum 12종 확정(D-14): FOOD/CAFE/BAR/BOARD_GAME/KARAOKE/ARCADE/PARK/CULTURE/SHOPPING/NIGHT_VIEW/MOVIE/ACTIVITY. ③ 리뷰 링크 안전성 검사 제거, `rel=nofollow`만 적용 + 리뷰 신고 기능(`course_review_reports`) 추가(D-15). ④ IP 리뷰 추가 어뷰징 방어(캡차 등) → V2(D-19). ⑤ 날씨 placeholder: OpenWeatherMap Current API(무료) + 역 좌표 기반, 30분 DB 캐시(D-17). ⑥ 코스 공유: SEO 공개 페이지(`/courses/{id}`) SSR + OG 태그, 이미지 공유는 V2(D-16). |
| v2.0 | 2026-06-25 | **워크플로우 전면 개편.** ① 추천 입력을 plan_type/budget 선택 → **지하철역 + 질의어(자연어)** 로 변경(동적 placeholder). ② **AI 추천 생성은 로그인 필수**(비로그인은 조회·평가만). ③ 무료 **재추천(regenerate) 삭제**, 생성 자체가 **하루 3회 무료**. ④ 생성 코스는 **전부 즉시 공개·DB 저장**(`is_saved` 게이트 제거). ⑤ 피드백을 👍/👎 → **100점 만점 5단위 점수 + 댓글 + 링크 통합 리뷰**(회원 1회/비로그인 IP)로 변경, 랭킹은 **베이지안 평균**. ⑥ `plan_type` enum 폐기 → **자유 `theme_tags`** + `companion_type`(4종) + `head_count`(인원). ⑦ 메인에서 역·테마·인원·예산 조건으로 전체 저장 코스 조회. ⑧ 추천 시 **유사 테마 고득점 코스 3개** 동반 노출. |
| v1.0 | 2026-06-24 | 최초 PRD. 단일 역 선택 기준 일관 적용. |

> **표기 규칙**
> - 우선순위: **P0**(MVP 필수) / **P1**(MVP 권장) / **P2**(차기)
> - 인수 조건은 `Given / When / Then` 체크리스트. 전부 충족 시 Story가 Done.
> - 🆕 = 원 TDD에 없어 통합 과정에서 보강한 항목.
> - ⚠️(가정) = 제품 맥락상 추론해 채운 값. 팀 확정 필요.

---

## 1. 제품 개요

### 1.1 한 줄 정의
**지하철역을 직접 고를 필요 없이, "오늘 뭐하고 놀지" 한 문장만 입력하면 AI가 문장 속 위치(동네·지명)를 파악해 가장 가까운 지하철역 기준으로 플랜(장소·동선 포함)을 즉시 짜주는 서비스.** 멀리 가지 않아도 가까운 역에서 알차게 놀 수 있게, "오늘 뭐하지?(What We Doin?)"의 고민을 한 번의 입력으로 해결한다. 친구끼리·혼자·연인 등 누구와의 외출이든 대응한다.

### 1.2 문제 / 타겟
- **문제**: 놀 곳·동선을 매번 검색·조합하는 비용이 크다. 후기·지도·예산을 따로 오가며 계획하기 번거롭고, "늘 가던 동네"만 맴돌게 된다.
- **타겟**: **멀리(자차·장거리) 이동이 부담스러운 Z세대**. 접근성 좋은 지하철로 가까운 여러 역을 가볍게 옮겨다니며 노는 사람들. 친구·혼자·연인 등 동행 무관. 모바일 웹 우선.
- **인사이트**: 지하철은 Z세대의 기본 이동수단. "이번엔 어느 역 가볼까"를 정하면 그 역에서 뭘 할지가 막막하다 → **역을 정하면 플랜이 따라오게** 한다.

### 1.3 핵심 가치 제안
1. **즉시성** — "어떻게 놀고 싶은지" 한 문장만 입력하면 위치·유형·예산까지 AI가 알아서 파악해 동선이 짜인 플랜이 나온다. 역을 따로 고를 필요가 없다.
2. **역 탐험** — "오늘은 이 역, 다음엔 저 역" 가까운 역들을 갈아타며 새로운 동네를 발견. 역별 인기 플랜이 탐험의 출발점.
3. **검증된 플랜** — 다른 사용자가 높은 점수(리뷰)를 준 인기 코스를 역·테마·인원·예산으로 탐색 가능.
4. **무료·무가입 경험** — 비로그인으로 생성·열람·피드백까지 전부 가능. 로그인은 개인화에서만.

### 1.4 성공 지표 (KPI) ⚠️(가정 — 목표치 협의 필요)
| 지표 | 정의 | 초기 목표 |
|---|---|---|
| 코스 리뷰율 | 생성 코스 중 리뷰(점수)가 달린 비율 | ≥ 25% |
| 코스 평균 점수 | 리뷰된 코스의 베이지안 평균 분포 | 모니터링(추천 품질 핵심 지표) |
| 역 탐험 다양성 | 사용자당 추천받은 서로 다른 역 수 | 모니터링(탐험성 핵심 지표) |
| 가입 전환율 | 비로그인 → 카카오 로그인 | ≥ 10% |

### 1.5 MVP 범위 (In / Out)
**In (P0~P1)**: **단일 자연어 질의어 입력**(위치·테마·예산·동행·인원을 모두 한 문장에서 추출) + 동적 placeholder, 질의어에서 지명이 검출되지 않거나 분류가 불충분하면 **추가 입력 Step(NEEDS_CLARIFICATION)** 으로 보완(역 검색 폴백 포함, US-A4), **로그인 사용자** 대상 AI 플랜 추천(하루 3회 무료) + **유사 테마 고득점 코스 3개 동반**, 생성 코스 **전부 즉시 공개·DB 저장**, 플랜 결과 화면, **100점·5단위 점수 + 댓글 + 링크 통합 리뷰**(회원 1회/비로그인 IP) + **베이지안 평균 랭킹**, 메인에서 역·테마·인원·예산 조건 저장 코스 탐색, 카카오 로그인·온보딩·마이페이지·탈퇴, 레이트리밋(비용 방어), 데이터 시딩/신선도 배치.
**In (P0~P1) 추가(v2.5)**: 장소 정보 사용자 제보(`POST /v1/places/{id}/report`) — 영업시간·별점·가격 직접 입력(검증 없음). 장소 카드에 "영업시간 알고 계신가요?" / "별점 남기기" CTA 노출.
**Out (V2+)**: 초기 화면의 **지도/역 이름 직접 검색을 통한 수동 역 선택**(D-20 — 단, US-A4 추가 입력 Step 안의 폴백 UI로만 유지), 다중 역 경유 플랜·역간 거리 검증, 출구별 만남 지점, 모바일 앱(React Native), 네이버 데이터 소스, 명시적 시간대(점심/저녁) 선택 UI(질의어로는 반영), 이미지 공유(OG 이미지 자동생성), 리뷰 신고 자동 숨김·캡차 등 추가 어뷰징 방어, 역 탐험 누적 기록(지나간 역 컬렉션), 무료 재추천(regenerate), **플레이스(장소) 단위 리뷰**(코스 리뷰와 별도 `place_reviews` 테이블), **영업시간 제보 검증 파이프라인**(playwright 검증·소형 분류모델·보상체계 — MVP의 단순 사용자 입력과 달리 자동 검증 포함, V2).

### 1.6 핵심 정책 결정 로그
| # | 결정 | 비고 |
|---|---|---|
| D-1 | **역은 1개만 선택** (다중역·거리검증 제외) | 2026-06-24 변경. `station_ids` 길이 1 고정, `validate` API·관련 에러·설정 제거 |
| D-2 | 지도=카카오맵 JS SDK, 장소=카카오 로컬 REST API + 크롤링 보조 | 네이버 보류 |
| D-3 | ~~비로그인도 생성 포함 전부 허용~~ → **AI 추천 생성은 로그인 필수**, 비로그인은 **조회·평가(리뷰)** 까지 허용 | 2026-06-25 변경(D-8). LLM 실비가 드는 생성만 로그인 게이트, 나머지는 무료·무가입 유지 |
| D-4 | 역 좌표는 역 중심(대표) 단일 1점 | 출구 단위는 V2 표시 전용 |
| D-5 | 외부 플레이스를 자체 `places` 마스터로 캐싱 | `place_id`는 자체 BIGINT로 통일 |
| D-6 | 영업시간/가격 신선도: 월 1회 배치 + 사용자 제보, 가격은 범주형 | 폐업은 `status=CLOSED`로 후보 제외 |
| **D-7** | **데이트 전용 → 일반 "오늘 뭐하지" 플래너로 확장** | 친구·혼자·연인·가족 모두 타겟. `companion_type`(누구랑) 4종 확정 |
| **D-8** | **추천 입력을 plan_type/budget 선택 → 지하철역 + 질의어(자연어)로 변경** | 2026-06-25. 질의어를 LLM으로 분류해 `theme_tags`·`budget_tier`·`companion_type`·`head_count`로 파싱. 입력창엔 최근 질문/날씨/시간대 기반 동적 placeholder 노출 |
| **D-9** | **무료 재추천(regenerate) 삭제, 생성 자체가 하루 3회 무료** | 2026-06-25. `regenerate`·`parent_request_id`·`served_from=SAVED_LIST`·`regenerate.free_count` 제거. 일일 한도는 로그인 user 기준 3회 |
| **D-10** | **생성 코스는 전부 즉시 공개·DB 저장** (`is_saved` 게이트 제거) | 2026-06-25. 메인 목록은 평가가 없어도 노출, 베이지안 평균으로 랭킹 |
| **D-11** | **피드백 모델 변경: 👍/👎 → 100점·5단위 점수 + 댓글 + 링크 통합 리뷰** | 2026-06-25. 신원당 1리뷰(회원=user, 비로그인=IP 해시). 코스 랭킹은 베이지안 평균(`rating.prior_mean`/`prior_count`) |
| **D-12** | **`plan_type` enum 폐기 → `theme_tag` enum 다중 선택으로 대체** | 2026-06-25. 질의어 LLM 분류 결과를 통제된 enum 값(12종)으로 매핑. 동의어·표기 흔들림 방지. |
| **D-13** | **추천 응답에 유사 테마 고득점 코스 3개 동반 노출** | 2026-06-25. 새로 만든 코스 + 같은(인접) 역·겹치는 테마 tag 중 베이지안 평균 상위 3개 |
| **D-14** | **`theme_tag` enum 12종 확정** | 2026-06-25. FOOD/CAFE/BAR/BOARD_GAME/KARAOKE/ARCADE/PARK/CULTURE/SHOPPING/NIGHT_VIEW/MOVIE/ACTIVITY. V2 추가 가능 |
| **D-15** | **리뷰 신고 기능 추가. 링크 안전성 검사 제거** | 2026-06-25. 링크 `rel=nofollow`만 적용, 도메인 화이트리스트 검사 없음. 부적절 리뷰는 신고(report) 기능으로 운영 대응 |
| **D-16** | **코스 공유 — SEO 공개 페이지(`/courses/{id}`) SSR 연계** | 2026-06-25. Next.js App Router SSR로 OG 태그(제목·썸네일·설명) 포함 공개 페이지. 링크 공유로 외부 유입. |
| **D-17** | **날씨 placeholder에 무료 기상 API(OpenWeatherMap Current) 사용** | 2026-06-25. 역 좌표로 현재 날씨 조회. 무료 티어(60 call/min) 내 운영. station_id별 캐시로 호출 최소화. |
| **D-18** | **`rating.prior_mean=50`, `prior_count=5` 확정** | 2026-06-25. 리뷰 없는 코스의 기본 베이지안 점수를 중립값 50으로 설정. |
| **D-19** | **IP 리뷰 어뷰징 추가 방어(캡차 등) → V2** | 2026-06-25. MVP는 `ratelimit.review_ip_daily` 일일 한도만 적용. 캡차·핑거프린트 등은 V2. |
| **D-20** | **초기 입력에서 지하철역 수동 선택 UI 제거 → 질의어 자연어에서 LLM이 지명/동네를 추출해 최근접 지원 역에 매핑** | 2026-07-01. `station_name`(LLM 추출) → `station_id`(DB resolve)로 서버에서 처리(D-1 단일 역 정책은 유지). 지명 언급이 없거나 매칭 실패 시 US-A4 추가 입력 Step에서 역 검색 UI(구 US-A2)를 폴백으로 노출. GPS 자동 수집은 계속 미사용(11장). |
| **D-21** | **`recommendation_requests.user_id`를 nullable로 변경(D-8과 11.1의 충돌 해소)** | 2026-07-01. D-8("생성은 로그인 필수, `user_id` NOT NULL")과 11.1("탈퇴 시 `recommendation_requests.user_id` NULL로 비식별화")이 스키마 레벨에서 충돌해 회원 탈퇴가 `NotNullViolationError`로 항상 실패하던 버그를 발견. 생성 시점의 "로그인 필수" 보장은 애플리케이션 레벨(`require_current_user`)에서 계속 유지하되, 탈퇴 후 비식별화를 위해 컬럼 자체의 `NOT NULL` 제약은 제거. |
| **D-22** | **`course_reviews.chk_review_identity` 제거(D-21과 동일 유형의 충돌)** | 2026-07-01. 로그인 리뷰(`ip_hash` 없음)를 탈퇴로 `user_id`까지 NULL 처리하면 "`user_id` 또는 `ip_hash` 중 하나는 필수" CHECK를 위반해 탈퇴가 `CheckViolationError`로 실패. 작성 시점 규칙은 `POST /reviews`에서 이미 앱 레벨로 보장되므로 DB 제약은 제거(재발 방지: 탈퇴 로직이 건드리는 모든 테이블의 제약을 D-21/D-22 계기로 전수 점검함). |
| **D-23** | **`GET /v1/courses`의 `theme`/`budget_tier`/`companion_type` 쿼리는 D-14 enum 코드(예: `FOOD`)만 허용, 자유 텍스트 한글 태그 불허** | 2026-07-01. 7.3 예시가 실제 `theme_tag` enum(D-14)이 아닌 자유 텍스트 한글("감성카페" 등)로 잘못 기술되어 있어, FE 구현(SCRUM-49)이 한글 문자열을 그대로 필터 값으로 전송하는 버그로 이어짐(동시에 BE도 `theme` 배열을 asyncpg에 바인딩 불가능한 방식으로 캐스팅해 500 발생). 유효하지 않은 enum 값은 `400 INVALID_THEME`/`INVALID_BUDGET_TIER`/`INVALID_COMPANION_TYPE`로 명확히 반려. |
| **D-24** | **코스 목록/상세 화면은 enum 코드 대신 한국어 라벨로 표시** | 2026-07-01. `theme_tags`/`budget_tier`/`companion_type`는 API 계약상 여전히 D-14/enums.py의 코드값을 그대로 주고받되(DB/API 변경 없음), FE가 원시 코드를 사용자에게 그대로 노출하던 버그를 발견해 온보딩(SCRUM-9)에서 이미 쓰던 한글 라벨 매핑을 `frontend/src/lib/enumOptions.ts`로 단일화. |
| **D-25** | **`GET /v1/users/me/courses`(내가 생성한 코스) 신규 추가** | 2026-07-01. `courses`는 콘텐츠 해시로 중복 제거되는 공유 엔티티라 소유자 컬럼이 없다(6.2.4). "내 코스"는 `recommendation_requests.user_id`(D-21)를 통해 역참조해 사용자가 요청한 적 있는 코스 집합으로 정의. US-D3 신설. |
| **D-26** | **코스 생성을 고정 선형 동선(1 place = 1 visit_order) → 단계(stage)별 복수 대안(1 stage = N개 옵션) 구조로 개편** | 2026-07-01. 식사·카페를 각각 2번씩 방문하는 식의 고정 동선은 특정 테마 투어가 아닌 이상 실제 코스 사용 패턴과 맞지 않는다는 피드백. 코스를 2~4개 단계로 나누고 각 단계에 1~3개 대안 장소를 배정, 사용자가 단계마다 하나를 선택하는 구조로 변경. LLM 프롬프트는 날씨(우천 시 실내 위주/맑을 때 야외 단계 포함 가능)를 반영. `course_places`의 `visit_order` → `stage_order`+`option_index`+`stage_label`, `walking_distance_to_next_km` → `walking_distance_from_station_km`(단계 내 대안은 병렬이라 "다음 장소 거리" 개념이 성립하지 않음). API 응답 `places[]` → `stages[].options[]`. `content_hash`도 단계+옵션 전체 구조 기준으로 변경. |

---

## 2. 사용자 & 접근 정책

### 2.1 비로그인 / 로그인 접근 정책 (핵심)
> **조회·평가는 비로그인으로 전부 경험 가능**하다. **LLM 실비가 드는 AI 추천 생성만 로그인 필수**(D-8). 그 외 개인화 기능도 로그인에서만.

| 구분 | 기능 | 비로그인 | 로그인 필요 |
|---|---|---|---|
| 메인 | 질의어(자연어) 단일 입력(위치 자동 추출) | ✅ | — |
| 메인 | 위치 미검출 시 역 검색 폴백(US-A4) | ✅ | — |
| 메인 | 저장 코스 목록 조회(역·테마·인원·예산 필터) | ✅ | — |
| 메인 | 코스 상세·리뷰 열람 | ✅ | — |
| 메인 | 코스 리뷰(100점·5단위 점수 + 댓글 + 링크) | ✅ (IP 기반) | — |
| 추천 | **AI 코스 추천(생성) `POST /courses/recommend`** | ❌ → 로그인 팝업 | ✅ (하루 3회 무료) |
| 추천 | 질의어 placeholder(최근 질문/날씨/시간대) | 기본값만 | ✅ (개인화) |
| 개인화 | 내 정보(누구랑·취향·연령대 등) 기반 추천 보정 | — | ✅ |
| 개인화 | 자주 가는 역·선호 테마/예산 저장 | — | ✅ |
| 개인화 | 마이페이지(조회/수정), 탈퇴 | — | ✅ |

- 비로그인 사용자는 **조회·리뷰만** 가능. 리뷰 1인 1표는 비로그인의 경우 **IP 해시** 기준(D-11). 생성 기능은 노출하되 누르면 카카오 로그인 팝업.
- **어뷰징 방어(비용 보호)**: 생성은 로그인 user 기준 일일 한도 3회(`ratelimit.user_daily=3`). 리뷰는 IP 기준 일일 상한으로 스팸 방지(`ratelimit.review_ip_daily`). LLM 실비 폭증과 평점 조작을 막는 핵심 장치.
- **로그인 팝업 트리거**: AI 추천 생성, 개인화 placeholder, 내 정보/마이페이지/자주 가는 역 저장 시도 시 카카오 로그인 팝업.
- 로그인 후 기존 비로그인 IP 리뷰는 `users.id`로 승격 가능(병합 규칙 6.6).

### 2.2 핵심 사용자 여정 (Happy Path)
```
[조회·무가입]  메인에서 역·테마·인원·예산 필터로 저장 코스 둘러보기 → 코스 상세·리뷰 열람 → 점수·댓글·링크 리뷰 남기기(IP)
[생성·로그인]  카카오 로그인 → 질의어 한 번 입력(동적 placeholder, 예: "홍대에서 친구랑 술 한잔하고 싶어")
                → AI가 질의어에서 위치(동네·지명)와 테마·예산·누구랑·인원을 함께 분류(D-20)
                → (위치 미검출/분류 불충분 시) 추가 입력 Step에서 역 검색 등으로 보완(US-A4, NEEDS_CLARIFICATION)
                → 해석된 최근접 역 반경의 후보 장소로 새 코스 생성(타임라인+지도)
                → 새 코스 + 유사 테마 고득점 코스 3개 함께 노출 → 코스는 즉시 DB 저장·공개
                → 점수(100점·5단위)·댓글·링크 리뷰 → 베이지안 평균으로 메인 랭킹에 반영
```

---

## 3. 기능 요구사항 — User Story & 인수 조건

### Epic A. 질의어 입력 & 위치 해석

> **v2.6(D-20) 개편**: 최초 화면에서 지하철역을 직접 고르는 절차를 없앴다. 사용자는 US-A3의 **질의어 입력 하나만** 마주치고, 그 문장 속 지명·동네를 AI가 해석해 역을 자동으로 정한다(US-A3a). 옛 US-A1(지도)·US-A2(역 검색)는 독립된 1차 진입점이 아니라, 위치 해석이 실패했을 때 US-A4가 띄우는 **보완 입력 Step 안의 폴백 컴포넌트**로만 남는다.

#### US-A3. 질의어(자연어) 단일 입력 & 동적 placeholder — **P0**
> 역도, 유형·예산도 따로 고르지 않고, "홍대에서 친구랑 술 한잔하고 싶어"처럼 **한 문장**만 입력하면 AI가 위치까지 포함해 오늘의 상황을 알아서 파악해주길 원한다. 입력창엔 상황에 맞는 예시가 떠 있으면 좋겠다.
> 관련: `POST /v1/courses/recommend`(query), `GET /v1/recommend/placeholder`, 9장 2단계, D-8, D-20

- [ ] Given 최초 화면, When 진입하면, Then **자유 텍스트 질의어 입력창 하나만** 제공된다(역 선택 UI·유형/예산 셀렉터 없음).
- [ ] Given 질의어 입력창, When 비워두면, Then **동적 placeholder**가 노출된다: 우선순위는 ① 로그인 사용자의 **최근 질문** → ② **현재 날씨/시간대**에 맞는 추천 문구 → ③ 기본 예시.
- [ ] Given 비로그인 사용자, When 질의어를 입력해 추천을 시도하면, Then 카카오 로그인 팝업이 뜨고(D-8), placeholder는 개인화 없이 날씨/시간대·기본 예시만 노출된다.
- [ ] Given 질의어 미입력(공백), When 추천을 시도하면, Then 추천 버튼이 비활성/안내되고 `INVALID_PARAMETER`를 방지한다.
- [ ] Given 서비스와 무관하거나 분류 불가한 질의어, When 추천하면, Then `INVALID_QUERY`("어떤 하루를 보내고 싶은지 알려주세요") 안내가 노출된다(9장 2단계).
- [ ] Given 로그인 사용자의 `preferred_theme_tags`/`preferred_budget`/`preferred_companion_type`가 있음, When 분류 결과가 비면, Then 해당 기본값으로 보정된다.

> **결정 D-8 반영**: 입력은 **질의어 하나**. 질의어는 9장 2단계에서 LLM이 `location_mention`(지명)·`theme_tags`·`budget_tier`·`companion_type`·`head_count`로 분류한다.
> **결정 D-1 반영**: 다중 역 선택 및 "추가 역 거리 제약 검증"은 MVP에서 **제외**한다. `POST /stations/validate`·`station.max_distance_km`·`TOO_MANY_STATIONS`·`STATION_TOO_FAR`는 미사용(V2 재검토).

#### US-A3a. 🆕 질의어 속 위치 자동 해석 → 최근접 역 매핑 — **P0**
> 문장 안에서 "홍대", "성수동", "합정역" 같은 지명·동네·역 이름을 알아서 읽어 가장 가까운 지원 역으로 바꿔주길 원한다. 지도를 보거나 역 이름을 따로 검색하고 싶지 않다.
> 관련: 9장 2~2.5단계, D-20

- [ ] Given 질의어에 역 이름이 직접 언급됨(예: "합정역"), When 분류하면, Then 해당 역 이름 그대로를 `location_mention`으로 추출한다.
- [ ] Given 질의어에 동네·상권명만 언급됨(예: "연남동", "경리단길"), When 분류하면, Then LLM이 가장 가까운 지원 역 이름으로 변환해 `location_mention`에 담는다.
- [ ] Given `location_mention`이 추출됨, When 서버가 처리하면, Then `stations` 테이블에서 이름 매칭으로 `station_id`를 resolve하고 이후 추천은 해당 역 반경 기준으로 진행된다.
- [ ] Given `location_mention` 매칭 실패(DB에 없는 지명), When 처리하면, Then `STATION_NOT_FOUND`로 실패하지 않고 US-A4 추가 입력 Step으로 전환되어 역 검색 폴백을 노출한다.
- [ ] Given 질의어에 지명이 전혀 없음, When 분류하면, Then `location_mention`은 없이(`missing_fields`에 `station_id` 포함) US-A4로 전환된다.

#### US-A4. 🆕 질의어 분류 결과 불충분 시 추가 입력 요청 Step — **P0**
> 질의어만으로 위치·인원·예산·동행 정보가 충분히 채워지지 않을 때, 빈 항목만 콕 집어 자연스럽게 추가로 물어보고 싶다. 처음부터 다시 쓰게 하지 않는다.
> 관련: `POST /v1/courses/recommend` 9장 2/2.5단계, D-20
>
> **PRD 비정합 해소(v2.6)**: 본 스토리는 SCRUM-60에서 "PRD v2.3 비정합"으로 플래그되어 있었다. v2.6에서 팀 결정으로 정식 채택하며, 위치(`station_id`) 누락도 `missing_fields`에 포함하도록 범위를 확장한다.

- [ ] Given 질의어 분류 시 `missing_fields`가 1개 이상(`station_id`/`companion_type`/`budget_tier` 등), When 처리하면, Then 클라이언트에 `NEEDS_CLARIFICATION`(200)과 함께 `partial_parsed_input`·`missing_fields[]`를 반환하고 LLM 코스 생성은 호출하지 않는다.
- [ ] Given `NEEDS_CLARIFICATION` 응답에 `missing_fields`가 `station_id`를 포함, When FE가 처리하면, Then 역 검색 UI(구 US-A2 폴백, `StationSearch` 재사용)가 표시되고, 선택 즉시 해당 `station_id`가 채워진다.
- [ ] Given `missing_fields`에 `companion_type`/`budget_tier`가 포함, When FE가 처리하면, Then 각각 4종 칩 입력이 표시된다.
- [ ] Given 추가 입력 Step, When 사용자가 모든 누락 필드를 완성하면, Then 기존 `partial_parsed_input`에 병합되어 `station_id` + 완성된 `parsed_input`으로 추천을 재요청한다(생성 한도 1회만 차감).
- [ ] Given 완전 분류 불가(`INVALID_QUERY`), When 처리하면, Then 추가 입력 Step 없이 "어떤 하루를 보내고 싶은지 알려주세요" 안내가 표시된다(일반 처리 유지).
- [ ] Given `users.preferred_*`/`home_station_id` 기본값이 있는 로그인 사용자, When `missing_fields`를 채울 때, Then 해당 필드에 기본값이 미리 채워진 채 표시되어 확인만으로 넘어갈 수 있다.

#### US-A1. 지도에서 지하철역 탐색·선택(위치 해석 실패 시 폴백) — **P1**
> ~~사용자로서, 지도를 움직여 원하는 지하철역 1개를 골라 코스의 기준점으로 삼고 싶다.~~ → v2.6(D-20): 최초 화면의 1차 진입점이 아니라, **US-A4 추가 입력 Step 안에서만** 노출되는 보조 선택 수단.
> 관련: `GET /v1/stations`

- [ ] Given US-A4 추가 입력 Step에서 `station_id`가 누락 필드로 표시됨, When "지도로 찾기"를 선택하면, Then 뷰포트 `bounds` 내 지하철역 마커만 표시된다(일반 POI 미표시).
- [ ] Given 역 마커, When 탭하면, Then 역명·노선 칩이 표시되고 해당 `station_id`가 채워진다.
- [ ] Given 미지원 역(`is_supported=false`), When 선택하면, Then 선택이 막히고 `STATION_NOT_SUPPORTED`("아직 지원하지 않는 역이에요") 안내가 노출된다.
- [ ] 🆕 Given GPS 미사용 정책(11장), When 지도를 처음 열면, Then 위치 자동수집 없이 기본 위치(서울 중심/마지막 본 영역)로 시작한다.

#### US-A2. 역 이름으로 검색(위치 해석 실패 시 폴백) — **P1**
> ~~지도를 헤매지 않고 역 이름을 입력해 빠르게 찾고 싶다.~~ → v2.6(D-20): US-A4 추가 입력 Step 안의 기본 폴백 컴포넌트(`StationSearch`)로 재사용.
> 관련: `GET /v1/stations/search`

- [ ] Given US-A4 추가 입력 Step의 역 검색창, When 역명을 입력하면, Then `is_supported=true`인 역만 최대 N건(`limit`) 자동완성으로 보인다.
- [ ] Given 검색 결과 항목, When 선택하면, Then 해당 `station_id`가 채워지고 추가 입력 Step이 다음 누락 필드로 진행되거나(모두 채워졌다면) 추천이 재요청된다.
- [ ] Given 결과 없음, When 검색하면, Then "검색 결과가 없어요" 빈 상태가 표시된다.

### Epic B. AI 코스 추천 (핵심)

#### US-B1. AI 코스 추천 생성 (질의어 기반, 위치 자동 해석) — **P0**
> 로그인 후, "어떻게 놀고 싶은지" 질의어 한 문장만으로 위치까지 포함해 동선이 잡힌 오늘의 플랜(코스) 한 벌을 AI가 만들어주길 원한다.
> 관련: `POST /v1/courses/recommend`, 9장 시퀀스, F-01/F-02/F-15, D-8, D-20

- [ ] Given 비로그인 사용자, When 추천을 요청하면, Then `UNAUTHORIZED`(401)로 막히고 카카오 로그인 팝업으로 유도된다(D-8).
- [ ] Given 클라이언트 요청, When 추천을 요청하면, Then `station_id`는 **선택값**이다 — 미포함 시 질의어에서 해석된 `location_mention`으로 서버가 최근접 지원 역을 resolve하며(D-20), 해석도 실패하면 `NEEDS_CLARIFICATION`(`missing_fields`에 `station_id` 포함, US-A4)으로 전환된다(단, resolve된 최종 역은 항상 정확히 1개, D-1 유지).
- [ ] Given 질의어, When 추천하면, Then LLM 분류 단계가 질의어를 `location_mention`·`theme_tags[]`·`budget_tier`·`companion_type`·`head_count`로 파싱하고 결과가 응답의 `parsed_input`에 포함된다(9장 2단계). 분류 불가 시 `INVALID_QUERY`.
- [ ] Given 선택한 역의 반경 5km 내 후보, When 추천하면, Then 후보가 부족하면 7km로 1회 확장하고, 그래도 없으면 `NO_COURSE_FOUND`를 반환한다.
- [ ] Given LLM 코스 생성, When 응답을 만들면, Then 모든 장소는 방문순서(`order`)·도보거리·`description`을 포함하고 `total_walking_distance_km`가 구간 합과 일치한다.
- [ ] Given LLM이 후보 풀 밖 장소를 반환(환각), When 검증하면, Then 위반 항목 제거 후 1회 재요청하고, 실패 시 `NO_COURSE_FOUND`를 반환한다.
- [ ] Given 동일 `Idempotency-Key` 재요청(더블클릭/재시도), When 호출하면, Then 새 LLM 호출 없이 이전 결과를 200으로 반환한다(일일 한도 미차감).
- [ ] Given 동일 분류 결과(역 + `parsed_input`) 캐시 존재, When 호출하면, Then `served_from=CACHE`로 즉시 반환한다.
- [ ] Given 추천 성공, When 응답하면, Then 생성된 코스가 **즉시 DB 저장·공개**되고(D-10) `disclaimer`("최근 한 달 이내 기준…") 문구가 포함된다.
- [ ] 🆕 Given 로그인 사용자의 개인화 정보(`preferred_companion_type`/`birth_year`/`gender`, 연인 동행 시 `dating_stage`), When 추천하면, Then 톤이 보정되고, 미입력이어도 기본 추천이 정상 동작한다.

#### US-B2. 유사 테마 고득점 코스 3개 동반 노출 — **P0**
> 새로 만든 코스 옆에, 비슷한 결의 검증된 인기 코스도 함께 보고 비교하고 싶다.
> 관련: `data.similar_top_courses`, 9장 7단계, D-13

- [ ] Given 추천 성공, When 응답하면, Then 같은(또는 인접) 역에서 `theme_tags`가 겹치는 기존 코스 중 **베이지안 평균 상위 3개**가 `similar_top_courses`로 함께 반환된다.
- [ ] Given 유사 코스 각 항목, When 표시하면, Then `course_id`·`theme_tags`·`bayesian_score`·`rating_count`·`preview_places`·`total_walking_distance_km` 요약이 보인다.
- [ ] Given 새로 만든 코스 자신, When 목록을 만들면, Then 유사 목록에서 제외된다(중복 방지).
- [ ] 🆕 Given 겹치는 테마의 기존 코스가 0건, When 응답하면, Then `similar_top_courses`는 빈 배열로 반환되고 새 코스만 노출된다.

> **재추천(regenerate) 삭제(D-9)**: 무료 재추천·저장 코스 폴백(구 US-B2)·`served_from=SAVED_LIST`는 제거. 결과가 아쉬우면 질의어를 바꿔 **새로 생성**(하루 3회 무료, US-B5)하거나 동반 노출된 유사 코스를 본다.

#### US-B3. 마음에 안 드는 장소 제외 후 재생성 — **P1**
> 코스 중 특정 장소만 빼고 같은 질의어로 다시 받고 싶다.
> 관련: `exclude_place_ids`, F-04

- [ ] Given 결과 코스의 특정 장소, When "이 장소 빼기" 후 같은 질의어로 다시 추천하면, Then 해당 `place_id`가 `exclude_place_ids`로 전달되어 후보에서 제외된다(일일 한도 1회 차감).
- [ ] Given 제외로 후보가 부족, When 재생성하면, Then 반경 확장(5→7km)을 거치고도 부족하면 `NO_COURSE_FOUND`를 반환한다.

#### US-B4. 🆕 추천 지연·실패 폴백 UX — **P0**
> AI가 느리거나 실패해도 빈 화면에 방치되지 않고 다음 행동을 안내받고 싶다.
> 관련: `LLM_UNAVAILABLE`, `UPSTREAM_UNAVAILABLE`, 4장 NFR

- [ ] Given 추천 요청 중, When 응답 대기가 길면, Then 스켈레톤/로딩 인디케이터와 "코스를 만드는 중…" 안내가 표시된다.
- [ ] Given `LLM_UNAVAILABLE`, When 응답하면, Then 동일 역·유사 테마의 기존 코스 제안 + 재시도 버튼이 노출된다(일일 한도 미차감).
- [ ] Given `UPSTREAM_UNAVAILABLE`(지도/플레이스 장애), When 발생하면, Then 친화 메시지로 안내하고 입력값(역·질의어)은 유지되어 재시도가 가능하다.
- [ ] Given 정상 경로, When 추천하면, Then 응답 P95 지연이 NFR 목표(4장) 이내여야 한다.

#### US-B5. 🆕 생성 횟수 제한(어뷰징·비용 방어) — **P0**
> (운영자) 로그인 어뷰징으로 LLM 실비가 폭증하지 않게, 생성은 하루 3회 무료로 제한하고 싶다.
> 관련: `ratelimit.user_daily=3`, DB 카운터, `429`, D-9

- [ ] Given 로그인 사용자, When 일일 생성 한도(`ratelimit.user_daily=3`)를 초과하면, Then `RATE_LIMIT_EXCEEDED`(429)로 차단되고 "내일 다시" 안내가 표시된다.
- [ ] Given 멱등 재요청·캐시 적중(`served_from=CACHE`)·실패(폴백) 응답, When 처리하면, Then 일일 한도는 **차감되지 않는다**(실 LLM 생성만 1회 차감).
- [ ] Given 자정 경계(KST), When 날짜가 바뀌면, Then 카운터가 `ratelimit.timezone` 기준으로 리셋된다(키 TTL 26h).
- [ ] Given 비로그인 리뷰 스팸, When IP 일일 리뷰 상한(`ratelimit.review_ip_daily`)을 초과하면, Then 429로 차단된다(평점 조작 방어).

### Epic C. 코스 결과 화면 & 피드백

#### US-C1. 코스 결과 타임라인 화면 — **P0**
> 추천 코스를 동선 순서대로 한눈에 보고, 지도에서 위치·이동 거리를 확인하고 싶다.

- [ ] Given 추천 응답, When 결과 화면을 그리면, Then 장소가 `order`순 타임라인으로 표시되고 각 카드에 이름·카테고리·가격대·영업시간·설명이 노출된다.
- [ ] Given 코스 장소들, When 지도를 그리면, Then 마커와 동선이 표시되고 `total_walking_distance_km`가 요약된다.
- [ ] Given 장소 카드의 `map_url`, When 탭하면, Then 외부 카카오맵 링크로 이동한다.
- [ ] Given 영업시간, When 표시하면, Then 구조화 데이터에서 파생된 `business_hours_text`를 보여주고 휴무일이 구분된다.
- [ ] Given 추천 응답의 `similar_top_courses`, When 결과 화면을 그리면, Then 새 코스 아래 "비슷한 결의 인기 코스" 섹션으로 고득점 3개가 함께 노출된다(US-B2).

#### US-C2. 코스 리뷰(점수 + 댓글 + 링크) — **P0**
> 다녀온 코스에 100점 만점 점수를 주고, 한마디 댓글과 참고 링크(블로그/지도 등)를 함께 남겨 다른 사람에게 도움을 주고 싶다.
> 관련: `POST /v1/courses/{id}/reviews`, `course_reviews`, D-11

- [ ] Given 비로그인/로그인 사용자, When 코스에 리뷰를 남기면, Then **1인 1리뷰**로 기록된다(로그인=`user_id`, 비로그인=`ip_hash`). 재요청 시 기존 리뷰가 **갱신(upsert)** 된다.
- [ ] Given 점수 입력, When 제출하면, Then 점수는 **0~100, 5점 단위**만 허용되고(`score % 5 = 0`) 위반 시 `INVALID_PARAMETER`로 거부된다.
- [ ] Given 리뷰 작성, When 제출하면, Then 점수(필수) 외 **댓글(선택)** 과 **링크 배열(선택)** 을 함께 저장할 수 있다.
- [ ] Given 리뷰 등록/수정/삭제, When 처리하면, Then 코스의 `rating_count`/`rating_sum`이 같은 트랜잭션에서 보정되고 `bayesian_score`가 재계산된다(단순 +1 금지).
- [ ] Given 코스 상세, When 열람하면, Then 평균 점수·리뷰 수와 리뷰 목록(점수·댓글·링크·작성시각)이 표시되며 비로그인도 열람 가능하다.
- [ ] Given 본인 리뷰, When 다시 진입하면, Then 기존 점수·댓글·링크가 채워져 수정/삭제할 수 있다.

> **베이지안 평균(D-11)**: 코스 랭킹/정렬은 단순 평균이 아니라 `bayesian = (C·m + Σscore) / (C + n)` (m=`rating.prior_mean`, C=`rating.prior_count`, n=리뷰 수). 리뷰 수가 적은 코스의 과대/과소평가를 완화한다.
> **저장 트리거 제거(D-10)**: 코스는 생성 즉시 공개되므로 리뷰가 "공개 트리거"가 아니다. 리뷰는 랭킹 신호로만 작용.

#### US-C3. 🆕 정보 신선도·폐업 표시 — **P1**
> 오래되거나 폐업한 정보로 헛걸음하지 않게, 코스에 신선도 경고를 보고 싶다.
> 관련: `freshness.stale_days`, `places.status`

- [ ] Given 코스 내 장소의 `last_synced_at`이 `stale_days`(30일) 초과, When 표시하면, Then "정보가 오래됐을 수 있어요" 배지가 코스 단위로 노출된다.
- [ ] Given 포함 장소에 `status='CLOSED'` 존재, When 표시하면, Then 폐업 경고가 노출되고 목록에서 후순위로 정렬된다.

#### US-C4. 사후 방문 설문 — **P2**
> 실제로 다녀왔는지 가볍게 남겨 추천·데이터 품질에 기여하고 싶다.
> 관련: `POST /v1/courses/{id}/visit-survey`

- [ ] Given 코스 열람 후, When 방문 설문(`visited`)에 응답하면, Then 결과가 기록된다.
- [ ] Given `visited=false`("정보가 달라요"), When 제출하면, Then 해당 장소 재검증 큐 우선순위가 상향된다.

### Epic D. 저장 코스 탐색

#### US-D1. 메인 저장 코스 목록(역·테마·인원·예산 필터, 비로그인 열람) — **P0**
> 메인 화면에서 역·테마·인원·예산 조건을 골라 검증된 인기 코스를 둘러보고 싶다. 만들기 전에 먼저 탐색.
> 관련: `GET /v1/courses`, D-10/D-11/D-12

- [ ] Given 비로그인 사용자, When 코스 목록을 요청하면, Then 인증 없이 공개 코스(생성 즉시 공개, D-10)가 조회된다.
- [ ] Given 메인 필터, When 조건을 적용하면, Then `station_id`·`theme`(테마 태그, 다중 가능)·`head_count`(인원)·`budget_tier`·`companion_type`로 필터링된다.
- [ ] Given 목록 항목, When 표시하면, Then `bayesian_score`·`rating_count`·`theme_tags`·`preview_places`·`total_walking_distance_km` 요약이 보인다.
- [ ] Given `sort` 필터, When 적용하면, Then 정렬(`score`=베이지안 평균 기본 / `recent`)이 반영된다.
- [ ] Given 결과가 많음, When 더보기하면, Then 커서 페이지네이션(`limit` 기본20·최대50, `next_cursor`)으로 이어진다.

#### US-D2. 🆕 빈 목록 → 첫 코스 만들기 유도 — **P1**
- [ ] Given 조건 부합 코스 0건, When 목록을 열면, Then 빈 상태 + "이 조건의 첫 코스를 만들어보세요" CTA가 표시되고 (로그인 후) 추천 입력 화면으로 연결된다.

#### US-D3. 🆕 내가 생성한 코스만 모아보기 — **P1**
> 그동안 내가 AI로 만든 코스만 따로 다시 찾아보고 싶다.
> 관련: `GET /v1/users/me/courses`, D-25

- [ ] Given 로그인 사용자, When "내 코스" 화면에 진입하면, Then 본인이 `POST /courses/recommend`로 요청해 받은 코스만 최근 요청순으로 모여 보인다.
- [ ] Given 비로그인 사용자, When "내 코스" 화면에 접근하면, Then 로그인 유도로 연결된다.
- [ ] Given 생성 이력 없음, When 목록을 열면, Then 빈 상태 + 홈으로 유도하는 안내가 표시된다.
- [ ] Given 탈퇴(11.1) 이후, When 목록을 조회하면, Then 비식별화(D-21)로 인해 더 이상 어떤 코스도 "내 코스"로 연결되지 않는다.

### Epic E. 인증 & 개인화 (카카오 단일)

#### US-E1. 카카오 로그인 — **P0**
> 카카오톡으로 간편하게 로그인해 개인화 기능을 쓰고 싶다.
> 관련: `POST /v1/auth/kakao`, 8장

- [ ] Given 로그인 트리거(개인화 진입), When 카카오 로그인을 진행하면, Then 클라이언트는 authorization code만 확보해 백엔드로 전달한다.
- [ ] Given code 수신, When 백엔드가 처리하면, Then 토큰 교환·프로필 조회는 서버에서만 수행되고(시크릿 미노출) `users` upsert 후 자체 JWT(access/refresh)가 발급된다.
- [ ] Given 신규 사용자, When 로그인 응답하면, Then `is_new_user=true`로 온보딩(약관·선택정보)으로 유도된다.
- [ ] Given 메인 추천 흐름 중, When 비로그인 사용자가 추천을 쓰면, Then 로그인이 강제되지 않는다.

#### US-E2. 🆕 온보딩 약관 동의 & 선택정보 입력 — **P0**
> 가입 시 꼭 필요한 동의만 받고, 개인화 정보는 부담 없이 선택 입력하고 싶다.
> 관련: `users.terms_agreed_at`/`privacy_agreed_at`/`marketing_agreed`, 5장, 11장

- [ ] Given 신규 사용자 온보딩, When 진입하면, Then 이용약관·개인정보 처리 동의가 **필수**, 마케팅 수신 동의가 **분리 선택**으로 제공된다.
- [ ] Given 필수 동의 미체크, When 다음으로 진행하면, Then 진행이 막히고, 동의 시각이 `*_agreed_at`에 저장된다.
- [ ] Given 선택 개인화 정보(누구랑/취향/성별·연령대 등), When 온보딩하면, Then "더 잘 맞는 플랜을 위해(선택)"로 안내되고 **건너뛰기**가 허용된다.
- [ ] Given 선택정보 미입력으로 가입 완료, When 추천을 쓰면, Then 기본 추천이 정상 동작한다.

#### US-E3. 토큰 갱신 & 로그아웃 — **P0**
> 자주 로그인하지 않아도 세션이 유지되되, 로그아웃하면 즉시 무효화되길 원한다.
> 관련: `POST /v1/auth/refresh`, `/logout`, 6.11, 11장

- [ ] Given access 토큰 만료, When refresh로 재발급하면, Then 새 access가 발급되고 refresh는 회전(rotation)되어 이전 `jti`는 폐기된다.
- [ ] Given refresh 토큰 재사용 감지, When 탐지하면, Then 해당 사용자의 모든 refresh 토큰이 폐기된다.
- [ ] Given 로그아웃, When 호출하면, Then 서버의 refresh 토큰이 무효화되어 더 이상 재발급되지 않는다.

#### US-E4. 마이페이지 조회·수정 — **P1**
> 관련: `GET/PATCH /v1/users/me`, 5장

- [ ] Given 로그인 사용자, When `/users/me`를 조회하면, Then 닉네임·선택 개인화 항목·동의 상태가 반환된다.
- [ ] Given 선택 항목(누구랑/선호 테마 태그/예산/성별·연령대/자주 가는 역), When 수정하면, Then 저장되고 이후 추천 기본값/보정·placeholder에 반영된다.

#### US-E5. 🆕 비로그인 → 로그인 리뷰 연속성(병합) — **P1**
> 관련: 2.1, 6.6 병합 규칙

- [ ] Given 비로그인(IP) 리뷰 후 로그인, When 연결하면, Then 해당 IP 해시 리뷰가 `users.id`로 승격될 수 있다.
- [ ] Given IP 리뷰와 user 리뷰가 같은 코스에 충돌, When 병합하면, Then user 리뷰 우선으로 중복 제거된다(코스 카운트 정합 보정).

#### US-E6. 회원 탈퇴 & 개인정보 파기 — **P0**
> 관련: `DELETE /v1/users/me`, 11.1 (PIPA)

- [ ] Given 로그인 사용자, When 탈퇴하면, Then `status=WITHDRAWN`과 동시에 닉네임·프로필·이메일·식별 항목이 파기/익명화된다.
- [ ] Given 통계 보존이 필요한 리뷰/요청 로그, When 탈퇴 처리하면, Then `user_id`가 익명화되고 식별 흔적(IP 해시 등)이 분리된다.
- [ ] Given 탈퇴, When 처리하면, Then DB `refresh_tokens`의 해당 사용자 레코드가 일괄 폐기된다.

### Epic F. 🆕 데이터·운영·비기능 (출시 게이트)

#### US-F1. 콜드스타트 장소 데이터 시딩 — **P0**
> 관련: 7.2.9 ETL/콜드스타트

- [ ] Given 서비스 오픈 전, When ETL을 수행하면, Then 지원 역 반경(5~7km) 장소가 `places`에 적재된다(카카오 로컬 API 기본 메타 + 보강).
- [ ] Given 미적재 역, When 노출하면, Then `is_supported=false`로 막혀 `STATION_NOT_SUPPORTED`로 안내된다.
- [ ] Given 동일 장소 재적재, When upsert하면, Then `(external_source, external_id)` UNIQUE로 중복 없이 갱신된다.
- [ ] Given 역 데이터 시딩, When `stations` 및 `station_lines`를 적재하면, Then `(external_source, external_id)` 기준 **upsert**로 처리되어 재실행 시 중복 없이 갱신된다(지방 도시 확장 시 동일 스크립트 재실행으로 대응).
- [ ] Given `station_lines` 미적재 상태, When `GET /v1/stations`를 호출하면, Then `lines` 필드가 빈 배열로 반환되어 노선 정보가 표시되지 않는다 — 시딩 시 반드시 함께 적재해야 한다.

#### US-F2. 월 1회 신선도 배치 & 폐업 처리 — **P1**
- [ ] Given `last_synced_at` 30일 초과, When 월 1회 배치를 돌리면, Then 해당 장소부터 재동기화되고 `last_synced_at`이 갱신된다.
- [ ] Given 폐업 확인, When 처리하면, Then `status='CLOSED'`로 표시되어 추천 후보에서 제외된다.
- [ ] Given 사용자 제보(visit-survey `visited=false`), When 수집하면, Then 재검증 큐 우선순위가 상향된다.

#### US-F3. 관찰성·비용 모니터링 — **P1**
- [ ] Given LLM 호출, When 추적하면, Then Langfuse trace에 프롬프트·토큰·모델별 비용·지연이 기록되되 개인식별정보·원문 위치는 포함되지 않는다.
- [ ] Given `served_from`(LLM/CACHE), When 집계하면, Then 캐시 적중률·실비 발생 비율을 대시보드로 확인할 수 있다.
- [ ] Given 애플리케이션 예외, When 발생하면, Then Sentry로 추적되고 `GET /health`가 ALB 헬스체크에 응답한다.

#### US-F4. 🆕 외부 데이터 수집 법무 게이트 — **P0(차단 조건)**
- [ ] Given 크롤링 파이프라인 도입, When 운영 전, Then 카카오 API 이용약관·DB권 검토에 대한 **법무 승인**이 선행된다(미승인 시 해당 소스 비활성).
- [ ] Given 캐싱 데이터, When 운영하면, Then 보관기간·출처 표기·갱신 정책이 문서화되어 준수된다.

---

## 4. 비기능 요구사항 (NFR) ⚠️(초기 제안값 — 협의 필요)

| 구분 | 항목 | 제안 목표 |
|---|---|---|
| 성능 | 추천 응답(LLM 경로) P95 | ≤ 8s |
| 성능 | 추천 캐시 경로 P95 | ≤ 500ms |
| 성능 | 목록/검색 API P95 | ≤ 300ms |
| 가용성 | 핵심 API 월 가용성 | ≥ 99.5% |
| 신뢰성 | LLM 실패 시 | 캐시/저장 코스 폴백으로 빈손 응답 0건 |
| 비용 | 추천 1건당 평균 LLM 비용 | 상한 설정 + 회귀 알람(Langfuse) |
| 보안 | access TTL / refresh 회전 | access 30분, refresh 회전·재사용 차단(11장) |
| 접근성 | 웹(1차) | 모바일 반응형, 주요 플로우 키보드/스크린리더 기본 대응 |
| 분석 | 핵심 지표 | 1.4 KPI(코스 리뷰율·평균 점수·캐시 적중률·가입 전환율) |

---

## 5. 회원정보 필드 설계

소셜 로그인 기본 정보 외, 추천 개인화를 위한 항목. **대부분 선택 입력**이며 수집 시 별도 동의(개인정보 최소수집).

| 필드 | 필수/선택 | 활용 목적 | 비고 |
|---|---|---|---|
| `nickname`, `profile_image_url` | 자동 | 화면 표시 | OAuth 동의 항목 수신 |
| `email` | 선택 | 사후 설문·알림 | 공급자 동의 시에만 |
| `gender` | 선택 | 데이트 유형·장소 톤 개인화 | 미입력 허용(UNKNOWN) |
| `birth_year` | 선택 | 연령대별 추천 보정 | 만나이/생일 대신 연도만(민감도 완화) |
| `dating_stage` | 선택 | 페르소나 직결(썸/초기/장기) | 추천 품질 영향 최대 |
| `preferred_companion_type` | 선택 | 질의어 분류 보정·기본 동행 | SOLO/FRIEND/COUPLE/FAMILY |
| `preferred_theme_tags` | 선택 | 질의어 분류 보정·추천 가중 | 자유 테마 태그(다중) |
| `preferred_budget` | 선택 | 예산 기본값/분류 보정 | |
| `home_station_id` | 선택 | 자주 가는 역 빠른 접근 | 즐겨찾기 |
| `marketing_agreed` | 필수(동의/거부) | 마케팅 알림 수신 | 법적 분리 동의 |

> **개인화 핵심 3종**: `dating_stage`·`birth_year`·`gender`. 모두 선택 입력이며 미입력 시에도 기본 추천이 정상 동작(가입 마찰 최소화).
> **개인정보 유의**: 성별·연령은 개인정보 → 수집·이용 목적 고지 및 동의 필요. 온보딩에서 "더 잘 맞는 코스를 위해(선택)"로 받고 건너뛰기 허용.

---

## 6. 기술 스택 & 데이터베이스

### 6.1 기술 스택

| 레이어 | 채택 기술 | 선정 이유 |
|---|---|---|
| **웹 클라이언트 (1차)** | Next.js (App Router) + TypeScript | MVP 웹 우선. SSR/SEO로 저장 코스 공개 페이지 노출, 타입 안전 API 계약. 카카오 맵·로그인 JS SDK 연동 |
| **모바일 클라이언트 (2차)** | React Native (Expo) | 웹 검증 후 확장. 웹과 도메인 타입(TS) 공유 |
| **백엔드 API** | Python 3.12 + FastAPI | Langfuse Python SDK 네이티브 지원이 핵심 선정 이유. `async/await`(asyncio)로 LLM·외부 API I/O 처리. SQLAlchemy 2.x(async) + asyncpg |
| **메인 DB** | PostgreSQL + PostGIS | 역 5km 반경 검색을 DB 레벨에서 처리(핵심). 트랜잭션 안정성 |
| **LLM** | Claude API (Anthropic) | 코스 조합/설명 생성. 단계적 모델 전략(저비용 필터 + 고급 톤). **Provider 추상화 인터페이스** 경유(OpenAI 등 타 공급자 전환 대비 — 12.4 참조) |
| **지도 렌더링** | 카카오맵 JS SDK | 역 마커·코스 동선 표시(웹 1차) |
| **장소 데이터 소스** | 카카오 로컬 REST API 1차 / 크롤링 보조 | 기본 메타는 API(무료 쿼터), 영업시간·가격은 크롤링 보강 후 `places` 캐싱 |
| **인증** | 카카오 OAuth 2.0(단일) + 자체 JWT | 카카오톡 단일 간편로그인. 세션은 자체 JWT. 비로그인도 메인 기능 전부 사용 |
| **인프라** | AWS (Seoul) | ECS on Fargate + RDS(PG) + ALB. 프론트는 Vercel(또는 정적 호스팅) |
| **IaC / 배포** | Terraform | 전 인프라 코드화, dev/prod workspace 분리 |
| **컨테이너** | Docker (ECR) | Python FastAPI 이미지 → ECR → ECS Fargate |
| **패키지 관리** | uv | 의존성 설치·가상환경·lock 파일. `pyproject.toml` 기반 |
| **DB 마이그레이션** | Alembic | SQLAlchemy 연동 스키마 버전 관리, 드리프트 방지 |
| **헬스/메트릭** | FastAPI 커스텀 라우터 | `GET /health`(ALB 헬스체크), `GET /metrics`(Prometheus, `prometheus-fastapi-instrumentator`) |
| **모니터링** | Sentry + CloudWatch | 예외 추적 + 인프라 메트릭·알람 |
| **LLM Observability** | Langfuse (Python SDK) | `langfuse` 패키지로 FastAPI 미들웨어 수준 통합. Claude 호출 트레이스·토큰 비용·지연·`served_from` 추적 |

> **PostGIS**: 역 좌표를 `geography(Point)`로 저장하면 `ST_DWithin`으로 5km 반경 내 장소를 인덱스 기반으로 빠르게 검색한다. (단일 역 정책으로 역간 거리 계산은 MVP에서 미사용.)

### 6.2 DB 스키마 (PostgreSQL 16 + PostGIS)

#### 6.2.1 `users`
```sql
-- 로그인은 카카오 단일이지만, 외부 데이터 소스(stations/places.external_source)에 재사용되므로 enum에 NAVER 유지.
CREATE TYPE oauth_provider AS ENUM ('KAKAO', 'NAVER');
CREATE TYPE gender_type AS ENUM ('MALE', 'FEMALE', 'OTHER', 'UNKNOWN');
CREATE TYPE dating_stage AS ENUM ('SOME', 'EARLY', 'LONGTERM', 'UNKNOWN');
CREATE TYPE budget_tier AS ENUM ('UNDER_30000', '30000_70000', '70000_150000', 'OVER_150000');
CREATE TYPE companion_type AS ENUM ('SOLO', 'FRIEND', 'COUPLE', 'FAMILY');   -- 누구랑(D-7, 4종 확정)

-- D-12: plan_type enum 폐기 → 통제된 테마 enum(D-14)으로 교체. 자유 text[]에서 변경.
CREATE TYPE theme_tag AS ENUM (
  'FOOD',        -- 맛집 / 식사
  'CAFE',        -- 카페 / 디저트
  'BAR',         -- 술 / 바 / 포차
  'BOARD_GAME',  -- 보드게임 / 방탈출
  'KARAOKE',     -- 노래방
  'ARCADE',      -- 오락 / 게임 / PC방
  'PARK',        -- 공원 / 산책 / 자연
  'CULTURE',     -- 전시 / 미술관 / 박물관
  'SHOPPING',    -- 쇼핑 / 마트 / 플리마켓
  'NIGHT_VIEW',  -- 야경 / 뷰 / 루프탑
  'MOVIE',       -- 영화관
  'ACTIVITY'     -- 클라이밍 / 볼링 / 스포츠 등 액티비티
);

CREATE TABLE users (
    id                  BIGSERIAL PRIMARY KEY,
    oauth_provider      oauth_provider NOT NULL DEFAULT 'KAKAO',
    oauth_id            VARCHAR(255) NOT NULL,
    email               VARCHAR(255),
    nickname            VARCHAR(50)  NOT NULL,
    profile_image_url   TEXT,
    gender              gender_type  DEFAULT 'UNKNOWN',
    birth_year          SMALLINT,
    dating_stage        dating_stage DEFAULT 'UNKNOWN',
    preferred_companion_type companion_type,            -- 기본 동행(질의어 분류 보정)
    preferred_theme_tags theme_tag[] DEFAULT '{}',      -- 선호 테마(통제 enum 다중)
    preferred_budget    budget_tier,
    home_station_id     BIGINT REFERENCES stations(station_id),
    terms_agreed_at     TIMESTAMPTZ NOT NULL,
    privacy_agreed_at   TIMESTAMPTZ NOT NULL,
    marketing_agreed    BOOLEAN DEFAULT FALSE,
    marketing_agreed_at TIMESTAMPTZ,
    status              VARCHAR(20) DEFAULT 'ACTIVE',   -- ACTIVE / WITHDRAWN
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (oauth_provider, oauth_id)
);
```

#### 6.2.2 (삭제) `devices` — 비로그인 디바이스
> **D-8/D-11로 제거.** 생성은 로그인 user 기준, 비로그인 리뷰는 IP 해시(`course_reviews.ip_hash`) 기준으로 식별·레이트리밋한다. 클라이언트 `X-Device-Id`는 더 이상 사용하지 않는다(레이트리밋 키는 `user_id`/`ip_hash`).

#### 6.2.3 `stations` — 지하철역 마스터
```sql
CREATE TABLE stations (
    station_id      BIGSERIAL PRIMARY KEY,
    external_id     VARCHAR(64),
    external_source oauth_provider,
    name            VARCHAR(100) NOT NULL,
    lat             DOUBLE PRECISION NOT NULL,
    lng             DOUBLE PRECISION NOT NULL,
    geom            GEOGRAPHY(Point, 4326) NOT NULL,    -- 역 대표(중심) 좌표. 반경 쿼리용
    is_supported    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_stations_geom ON stations USING GIST (geom);

CREATE TABLE station_lines (                            -- 환승 노선 (N:M)
    station_id  BIGINT REFERENCES stations(station_id),
    line_no     VARCHAR(20) NOT NULL,
    PRIMARY KEY (station_id, line_no)
);
```
> 자체 `station_id` PK로 외부 의존도를 낮추고, `external_id`(+출처)로 매핑. `geom`은 역 중심 단일 1점(D-4). 출구 단위는 V2 표시 전용.
> **시딩 정책**: `stations` 적재는 `(external_source, external_id)` 기준 **upsert**로 처리(중복 방지·재적재 안전). 서울 외 지방 도시(대구·부산 등) 확장 시 동일 스크립트 재실행으로 대응 가능하도록 설계. `station_lines`는 `GET /v1/stations` 응답의 `lines` 필드 소스로, **초기 시딩 시 반드시 함께 적재**해야 한다(미적재 시 노선 정보 빈값으로 노출).

#### 6.2.4 `courses` — 코스 (생성 즉시 공개)
```sql
-- D-12/D-14: plan_type enum 폐기 → theme_tag enum[] 12종으로 대체.
CREATE TABLE courses (
    course_id       BIGSERIAL PRIMARY KEY,
    station_id      BIGINT NOT NULL REFERENCES stations(station_id),  -- 기준 역(D-1 단일). V2 다중역은 별도 조인 테이블로 확장
    theme_tags      theme_tag[] NOT NULL DEFAULT '{}',    -- 질의어 분류로 선택한 테마(통제 enum 다중, D-14)
    budget_tier     budget_tier NOT NULL,
    companion_type  companion_type NOT NULL,             -- 누구랑(4종)
    head_count      SMALLINT,                            -- 인원(질의어에서 추출, 미상 시 NULL)
    query_text      TEXT,                                -- 생성 origin 질의어(비식별 스냅샷)
    places          JSONB NOT NULL,                      -- 장소 구성 + 동선 스냅샷(불변, 서빙·캐시용)
    total_walking_distance_km NUMERIC(4,1),
    rating_count    INTEGER DEFAULT 0,                   -- 리뷰 수(n)
    rating_sum      INTEGER DEFAULT 0,                   -- 점수 합(Σscore) → 평균 산출용
    bayesian_score  NUMERIC(5,2) DEFAULT 0,              -- 베이지안 평균(랭킹/정렬 캐시값, 리뷰 변동 시 재계산)
    content_hash    VARCHAR(64) UNIQUE,                  -- 동일 구성 중복 방지(코스 재사용)
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_courses_station    ON courses (station_id);
CREATE INDEX idx_courses_theme      ON courses USING GIN (theme_tags);    -- 유사 테마 매칭/필터(enum[] 겹침 &&)
CREATE INDEX idx_courses_rank       ON courses (station_id, bayesian_score DESC);
CREATE INDEX idx_courses_filter     ON courses (budget_tier, companion_type, head_count);
```
> - 코스에는 **생성자 식별정보를 저장하지 않는다(비식별)**. 생성 즉시 공개(D-10)이므로 `is_saved` 게이트 없음.
> - **라이프사이클**: 추천 생성 시점(9장 6단계)에 `content_hash` 기준 **UPSERT**(`INSERT ... ON CONFLICT (content_hash) DO UPDATE SET updated_at=now() RETURNING course_id`). 동일 구성이면 기존 `course_id` 재사용(리뷰·점수 보존).
> - **`content_hash`**: `sha256(station_id + 정렬된 theme_tags + budget_tier + companion_type + head_count + 방문순서대로 나열한 place_id 목록)`. 동선 순서가 다르면 다른 코스.
> - **베이지안 평균(D-11)**: `bayesian_score = (C·m + rating_sum) / (C + rating_count)` (m=`rating.prior_mean`, C=`rating.prior_count`). 리뷰 등록/수정/삭제 트랜잭션에서 `rating_count`/`rating_sum` 갱신 후 재계산.
> - **유사 테마 고득점 3개(D-13, 9장 7단계)**: `WHERE station_id = ? AND theme_tags && ?(겹침) AND course_id <> 새코스 ORDER BY bayesian_score DESC LIMIT 3`. GIN 인덱스로 배열 겹침 검색.
> - **`places` JSONB vs `course_places`(6.2.10)**: `courses.places`는 생성 시점 가격·영업시간·동선을 박제한 **불변 스냅샷**(조인 없이 즉시 서빙). 정규화 테이블은 생성 시 함께 채워 분석·필터·place 단위 집계에 사용.

#### 6.2.5 `recommendation_requests` — 추천 요청 로그
```sql
-- D-9: regenerate 삭제(SAVED_LIST 폴백 제거). served_from은 LLM/CACHE만.
CREATE TYPE served_from AS ENUM ('LLM', 'CACHE');

CREATE TABLE recommendation_requests (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT REFERENCES users(id),  -- D-8: 생성 시점엔 앱 레벨에서 항상 로그인 사용자 값을 채움. D-21: 탈퇴 시 11.1 비식별화(NULL)를 위해 컬럼 자체는 nullable
    station_id        BIGINT NOT NULL REFERENCES stations(station_id),  -- D-20: 질의어 location_mention을 서버가 resolve한 결과(레코드 시점엔 항상 확정)
    query_text        TEXT NOT NULL,                     -- 입력 질의어(자연어)
    parsed_input      JSONB,                             -- 분류 결과 {location_mention, theme_tags: theme_tag[], budget_tier, companion_type, head_count}
    exclude_place_ids BIGINT[] DEFAULT '{}',             -- 장소 제외 재생성(US-B3)
    served_from       served_from NOT NULL,
    idempotency_key   VARCHAR(64),
    course_id         BIGINT REFERENCES courses(course_id),
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX uq_rec_idem ON recommendation_requests (user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_rec_recent ON recommendation_requests (user_id, created_at DESC);  -- 최근 질문 placeholder용
```
> **일일 한도(D-9)**: 무료 재추천 개념 없이 **생성 1건 = 1회 차감**. `served_from='LLM'` 신규 생성만 카운트(멱등 재요청·`CACHE` 적중·실패 폴백은 미차감). 한도는 `recommendation_requests`에서 `served_from='LLM'` 오늘(KST) 건수 COUNT < `ratelimit.user_daily(=3)`.
> **최근 질문 placeholder(US-A3)**: `idx_rec_recent`로 사용자 최근 `query_text`를 빠르게 조회해 입력창 placeholder 1순위로 사용.

#### 6.2.6 `course_reviews` — 코스 리뷰(점수 + 댓글 + 링크)
```sql
-- D-11: 👍/👎 폐기. 100점·5단위 점수 + 댓글 + 링크 통합 리뷰. 신원당 1리뷰(회원=user, 비로그인=ip_hash).
CREATE TABLE course_reviews (
    id          BIGSERIAL PRIMARY KEY,
    course_id   BIGINT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    user_id     BIGINT REFERENCES users(id),                 -- 로그인 리뷰
    ip_hash     VARCHAR(64),                                 -- 비로그인 리뷰 식별(IP 해시/마스킹)
    score       SMALLINT NOT NULL,                           -- 0~100, 5단위
    comment     TEXT,                                        -- 댓글(선택)
    links       JSONB NOT NULL DEFAULT '[]',                 -- 참고 링크 배열(선택), 예: ["https://..."]
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    -- D-22: chk_review_identity 제거. 작성 시 user_id/ip_hash 중 하나 필수인 규칙은
    -- 앱 레벨(POST /reviews)에서 이미 보장되며, 탈퇴 비식별화(11.1)로 user_id를 NULL
    -- 처리할 때 ip_hash 없는(로그인) 리뷰가 둘 다 NULL이 되는 정상 케이스와 충돌했음.
    CONSTRAINT chk_review_score CHECK (score BETWEEN 0 AND 100 AND score % 5 = 0)
);
CREATE UNIQUE INDEX uq_review_user ON course_reviews (course_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX uq_review_ip   ON course_reviews (course_id, ip_hash) WHERE user_id IS NULL;
CREATE INDEX idx_reviews_course ON course_reviews (course_id, created_at DESC);
```
> - DDL 순서상 `courses`가 `course_reviews`보다 먼저 생성.
> - **1인 1리뷰·카운트 정합성**: 부분 유니크 인덱스로 중복 차단, 재호출 시 `ON CONFLICT ... DO UPDATE`로 점수·댓글·링크 갱신(upsert). 등록/수정/삭제 시 **같은 트랜잭션에서** `courses.rating_count`/`rating_sum` 보정 후 `bayesian_score` 재계산(단순 +1 금지).
> - **베이지안 평균**: `bayesian_score = (C·m + rating_sum)/(C + rating_count)` (m=`rating.prior_mean`, C=`rating.prior_count`). 메인/유사 코스 랭킹에 사용.
> - **비로그인 IP 식별**: `ip_hash`는 원문 IP를 해시/마스킹한 값만 저장(11장). 스팸은 `ratelimit.review_ip_daily`로 방어.
> - **로그인 전환 병합(6.6)**: 비로그인(`ip_hash`) 리뷰를 로그인 시 `user_id`로 승격하되 이미 user 리뷰가 있으면 user 우선 중복 제거.
> - **place 단위 리뷰 → V2**: 장소 단위 리뷰(`place_reviews`)는 V2로 이관. MVP에서는 코스 단위 리뷰만 제공. 장소 제외는 재생성 시 `exclude_place_ids`(US-B3)로 대체.
> - **리뷰 링크**: 저장만 하며 도메인 화이트리스트·안전성 검사 없음(D-15). 클라이언트에서 `rel="nofollow noopener"` 처리.

#### 6.2.6b `course_review_reports` — 리뷰 신고 (D-15)
```sql
CREATE TYPE report_reason AS ENUM (
  'SPAM',          -- 스팸/광고
  'INAPPROPRIATE', -- 불건전/욕설
  'WRONG_INFO',    -- 잘못된 정보
  'OTHER'
);

CREATE TABLE course_review_reports (
    id          BIGSERIAL PRIMARY KEY,
    review_id   BIGINT NOT NULL REFERENCES course_reviews(id) ON DELETE CASCADE,
    user_id     BIGINT REFERENCES users(id),              -- 로그인 신고
    ip_hash     VARCHAR(64),                              -- 비로그인 신고
    reason      report_reason NOT NULL,
    comment     TEXT,                                     -- 추가 설명(선택)
    created_at  TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT chk_reporter CHECK (user_id IS NOT NULL OR ip_hash IS NOT NULL)
);
CREATE UNIQUE INDEX uq_report_user ON course_review_reports (review_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX uq_report_ip   ON course_review_reports (review_id, ip_hash) WHERE user_id IS NULL;
```
> - **운영 처리**: 신고 누적 수(`report_count`, 별도 집계 또는 COUNT 쿼리)가 임계치(`report.hide_threshold`, `app_config`)를 넘으면 관리자 검토 대기 상태로 표시. 자동 숨김은 V2.
> - 신고 자체는 공개 정책에 영향 없음(코스 즉시 공개 D-10 유지). 운영자가 수동 비공개 처리.

#### 6.2.7 `course_cache`
```sql
CREATE TABLE course_cache (
    cache_key   VARCHAR(64) PRIMARY KEY,                -- hash(station_id + 정규화된 parsed_input)
    result      JSONB NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL                    -- 기본 now()+14d
);
```
> 캐시 키는 자연어 원문이 아니라 **분류 결과(parsed_input)** 기준. 동일 역 + 동일 분류면 LLM 재호출 없이 `served_from=CACHE` 반환(9장 3단계).

#### 6.2.8 `app_config` — 운영 설정
```sql
CREATE TABLE app_config (
    key         VARCHAR(100) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now()
);
-- 초기값 (D-1로 station.max_distance_km 제거 / D-9로 regenerate.free_count·guest 생성 한도 제거)
-- ('cache.ttl_days', '14')
-- ('ratelimit.user_daily', '3')                -- 로그인 사용자 일일 무료 생성 한도(D-9)
-- ('ratelimit.review_ip_daily', '20')          -- 비로그인 IP 일일 리뷰 상한(평점 조작·스팸 방어)
-- ('ratelimit.place_report_ip_daily', '10')    -- 비로그인 IP 일일 장소 제보 상한(v2.5)
-- ('ratelimit.timezone', 'Asia/Seoul')         -- 일일 카운터 리셋 기준 타임존
-- ('rating.prior_mean', '50')                  -- 베이지안 사전 평균 m (D-18: 중립값 50)
-- ('rating.prior_count', '5')                  -- 베이지안 사전 표본 수 C(리뷰 적은 코스 평활)
-- ('freshness.sync_interval_days', '30')       -- 장소 재동기화 주기
-- ('freshness.stale_days', '30')               -- '오래된 정보' 표시 기준
-- ('recommend.radius_base_km', '5'), ('recommend.radius_expand_km', '7')  -- 후보 검색 반경/확장
-- ('recommend.similar_top_n', '3')             -- 유사 테마 동반 노출 개수(D-13)
-- ('report.hide_threshold', '5')              -- 신고 누적 시 관리자 검토 대기 임계치(D-15)
```
> **레이트리밋 카운터(DB)**: 생성은 `recommendation_requests`에서 `served_from='LLM'`이고 `created_at` 오늘(KST) 건수 COUNT, 비로그인 리뷰는 `course_reviews`에서 `ip_hash` 오늘(KST) 건수 COUNT. 초과 시 `429 RATE_LIMIT_EXCEEDED`.

#### 6.2.9 `places` — 장소 마스터 (외부 플레이스 캐시)
```sql
CREATE TABLE places (
    place_id        BIGSERIAL PRIMARY KEY,
    external_id     VARCHAR(64) NOT NULL,
    external_source oauth_provider NOT NULL,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(50),
    address         TEXT,
    lat             DOUBLE PRECISION NOT NULL,
    lng             DOUBLE PRECISION NOT NULL,
    geom            GEOGRAPHY(Point, 4326) NOT NULL,    -- 역 5km 반경 후보 검색(ST_DWithin)
    price_range     VARCHAR(50),
    business_hours  JSONB,
    map_url         TEXT,
    phone           VARCHAR(30),
    thumbnail_url   TEXT,
    theme_tags           theme_tag[] DEFAULT '{}',      -- ETL 시 카카오 카테고리 코드 → enum 매핑(카카오 API 미제공, 자동 분류)
    user_rating_sum      INTEGER DEFAULT 0,             -- 사용자 제보 별점 합 (v2.5, place-level 단순 평점)
    user_rating_count    INTEGER DEFAULT 0,             -- 사용자 제보 별점 수 → avg = sum/count
    status          VARCHAR(10) DEFAULT 'OPEN',         -- OPEN / CLOSED / UNKNOWN
    last_synced_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (external_source, external_id)
);
CREATE INDEX idx_places_geom     ON places USING GIST (geom);
CREATE INDEX idx_places_category ON places (category);
CREATE INDEX idx_places_theme    ON places USING GIN (theme_tags);  -- 후보 조회 시 theme_tag 필터용
```
> - 추천 4단계(후보 조회)는 `ST_DWithin`으로 역 반경 후보를 뽑되 `status='CLOSED'` 제외.
> - **신선도(D-6)**: ① 월 1회 배치로 `last_synced_at` 30일 초과분 재동기화, 폐업 시 `status='CLOSED'`. ② 사용자 제보(visit-survey `visited=false`)는 재검증 큐 우선순위 상향. ③ 가격은 범주형 `price_range`만 유지.
> - **ETL**: 기본 메타는 카카오 로컬 REST API(`external_source='KAKAO'`). 동일 장소는 `(external_source, external_id)` UNIQUE upsert.
> - **카카오 API 미제공 항목 처리 정책(v2.5 확정)**: 카카오 로컬 API는 **평점·영업시간을 정책상 제공하지 않으며 크롤링으로도 수집 불가**. 구체적으로:
>   ① `business_hours` — 카카오 API 미제공, 크롤링 불가. **MVP: `POST /v1/places/{id}/report`로 사용자가 직접 입력(검증 없이 즉시 저장).** 미확인 시 `null` 유지 후 장소 카드에 "영업시간 알고 계신가요? — 제보하기" CTA 노출.
>   ② `price_range` — API 미제공. **MVP: `POST /v1/places/{id}/report`로 사용자 입력 허용.** 크롤링 보강은 법무 확인 후(크롤링만 게이트, API 사용은 OK).
>   ③ `user_rating_sum` / `user_rating_count` — 카카오 API 미제공 평점을 대체. **MVP: `POST /v1/places/{id}/report`에서 `rating`(1.0~5.0, 0.5단위) 제보 시 sum·count 갱신. 장소 카드에 "별점 남기기" CTA.**
>   ④ `thumbnail_url` — API 미제공. 크롤링 보강 가능 여부 법무 확인 필요(크롤링만 게이트).
>   ⑤ `theme_tags` — API 미제공. ETL 시 카카오 `category_group_code`(예: `FD6`, `CE7`, `AT4`)를 `theme_tag` enum으로 매핑하는 **카테고리 매핑 테이블**로 자동 분류(매핑 불가 항목은 빈 배열 유지).
> - **콜드스타트**: recommend는 `places`에서만 후보를 뽑으므로 오픈 전 지원 역 반경(5~7km) 사전 적재 필수(US-F1). 미적재 역은 `is_supported=false`.

#### 6.2.10 `course_places` — 코스 구성 장소 (단계별 복수 대안, D-26)
```sql
CREATE TABLE course_places (
    course_id                      BIGINT  NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    stage_order                    SMALLINT NOT NULL,       -- 몇 번째 단계인지 (예: 1=저녁 식사, 2=카페)
    option_index                   SMALLINT NOT NULL DEFAULT 1,  -- 그 단계 안에서 몇 번째 대안인지
    stage_label                    VARCHAR(30) NOT NULL,    -- 단계 이름(예: "저녁 식사", "카페/디저트")
    place_id                       BIGINT  NOT NULL REFERENCES places(place_id),
    description                    TEXT,                    -- 이 대안 맥락의 LLM 설명(스냅샷)
    walking_distance_from_station_km NUMERIC(4,1),           -- 역 기준 거리(단계 간 "다음 장소까지 거리" 개념은 성립하지 않음)
    created_at                     TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (course_id, stage_order, option_index)
);
CREATE INDEX idx_course_places_place ON course_places (place_id);
```
> - **(D-26)** 코스는 2~4개의 단계(stage)로 구성되고, 각 단계는 1~3개의 대안(option)을 가진다. 사용자는 각 단계에서 대안 하나를 골라 자신만의 동선을 완성한다(모든 조합이 유효 — 단계 간 이동 거리는 검증하지 않음, D-1 단일 역 정책과 별개).
> - 코스 생성 즉시(9장 6단계) `courses.places` 스냅샷과 함께 채운다(D-10, `is_saved` 게이트 없음).
> - API의 `place_id`는 자체 마스터(`places.place_id`, BIGINT)로 통일. 외부 식별자는 `map_url` 등 외부 링크에만 사용.

#### 6.2.11 공통 규약 — `updated_at` 자동 갱신 / refresh 토큰 저장소
```sql
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
-- 예: CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
--     FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- refresh 토큰 저장소 (DB)
CREATE TABLE refresh_tokens (
    jti         VARCHAR(64) PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_agent  TEXT,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ
);
CREATE INDEX idx_rt_user ON refresh_tokens (user_id);
```
> **refresh 토큰 저장소(DB)**: `refresh_tokens` 테이블에 저장. 회전: refresh 사용 시 기존 `jti` `revoked_at` 설정 후 신규 발급(재사용 감지 시 사용자 전 토큰 폐기). 로그아웃/탈퇴: `WHERE user_id = ?` 일괄 `revoked_at` 설정(또는 DELETE). 만료된 레코드는 정기 배치로 정리.

---

## 7. API 스펙

> 공통 헤더: `Content-Type: application/json`, `Authorization: Bearer {token}`(생성·개인화 필수, 조회·리뷰는 선택), `Idempotency-Key`(생성 계열 POST 권장). `X-Device-Id`는 폐기(D-8/D-11).
> `place_id`는 자체 마스터 ID(`places.place_id`, 정수). 외부 식별자는 `map_url`에만 사용.
>
> **인증 게이트(D-8)**: `POST /v1/courses/recommend`는 **로그인 필수**(비로그인 시 401 `UNAUTHORIZED`). 코스 조회·리뷰는 비로그인 허용(리뷰는 IP 해시로 식별).
>
> **공통 응답 스키마**: `{ "success": bool, "data": object|null, "error": { "code": string, "message": string } | null }`. 성공 시 `error=null`, 실패 시 `data=null`. `error.message`는 사용자 표시용 한국어.
>
> **멱등성**: `POST /v1/courses/recommend`는 `Idempotency-Key` 동일 재요청 시 **새 LLM 호출 없이 이전 결과 반환**(중복 과금·한도 차감 방지).
>
> **페이지네이션**: 커서 기반. `?limit=20&cursor={opaque}`, 응답 `data.next_cursor`(없으면 null). `limit` 기본 20·최대 50.

### 7.1 GET /v1/stations — 지하철역 마커 조회
> v2.6(D-20): 최초 화면 1차 진입점이 아니라 US-A4 추가 입력 Step(지도 폴백, US-A1)에서만 호출된다.
```
GET /v1/stations?bounds={sw_lat},{sw_lng},{ne_lat},{ne_lng}
```
```json
{ "success": true,
  "data": { "stations": [
    { "station_id": 239, "name": "합정", "lines": ["2","6"], "lat": 37.549463, "lng": 126.913739, "is_supported": true }
  ] }, "error": null }
```

### 7.2 GET /v1/stations/search — 역 이름 검색
> v2.6(D-20): 최초 화면 1차 진입점이 아니라 US-A4 추가 입력 Step(역 검색 폴백, US-A2)에서만 호출된다.
`is_supported=true`만 반환.
```
GET /v1/stations/search?q=합정&limit=10
```
```json
{ "success": true,
  "data": { "stations": [ { "station_id": 239, "name": "합정", "lines": ["2","6"] } ] }, "error": null }
```

> **삭제(D-1)**: 구 `POST /v1/stations/validate`(추가 역 거리 검증)는 단일 역 정책으로 MVP에서 제거.

### 7.3 GET /v1/courses — 메인 코스 목록 (역·테마·인원·예산 필터, 비로그인 열람)
```
GET /v1/courses?station_id=239&theme=CAFE&theme=FOOD&companion_type=COUPLE&head_count=2&budget_tier=30000_70000&sort=score&limit=20&cursor=
```
| 쿼리 | 설명 |
|---|---|
| `station_id` | 선택. 특정 역 기준 필터 |
| `theme` | 선택·**반복 가능**(다중 테마 태그). `theme_tag` enum 코드(D-14)만 허용. 하나라도 겹치면 매칭(배열 `&&`) |
| `companion_type` | 선택. `SOLO`/`FRIEND`/`COUPLE`/`FAMILY` |
| `head_count` | 선택. 인원 |
| `budget_tier` | 선택. `UNDER_30000`/`30000_70000`/`70000_150000`/`OVER_150000` |
| `sort` | `score`(기본, 베이지안 평균) / `recent` |
| `limit`, `cursor` | 커서 페이지네이션. 기본 20·최대 50 |

```json
{ "success": true,
  "data": { "courses": [
    { "course_id": 5012, "station_id": 239, "theme_tags": ["CAFE","FOOD"],
      "budget_tier": "30000_70000", "companion_type": "COUPLE", "head_count": 2,
      "bayesian_score": 82.4, "rating_count": 38,
      "preview_places": ["00카페","00식당","00공원"], "total_walking_distance_km": 1.2 }
  ], "total": 14, "next_cursor": null }, "error": null }
```
- **인증 불필요**. 생성 즉시 공개(D-10)라 모든 공개 코스가 대상. 조건 부합 0건이면 빈 배열 + "첫 코스 만들기" 유도(US-D2).
- **랭킹**: `sort=score`는 `bayesian_score DESC`(D-11). 동점은 `rating_count`·`created_at`로 타이브레이크.
- **신선도 표시**: 조회 시 포함 장소의 `last_synced_at`/`status`를 조인해 코스 단위 동적 산출. `stale_days`(30일) 초과 시 배지, `CLOSED` 포함 시 경고 + 후순위.
- **필터 값 검증**(D-23): `theme`/`budget_tier`/`companion_type`이 각 enum에 없는 값이면 `400`(`INVALID_THEME`/`INVALID_BUDGET_TIER`/`INVALID_COMPANION_TYPE`). FE는 `theme_tags`/`budget_tier`/`companion_type`을 사용자에게 표시할 때 enum 코드가 아닌 한국어 라벨로 변환한다(D-24, `frontend/src/lib/enumOptions.ts`).

### 7.3b GET /v1/users/me/courses — 내가 생성한 코스 (US-D3, D-25)
```
GET /v1/users/me/courses?limit=20&cursor=
```
- **로그인 필수**. `courses`는 소유자 컬럼이 없는 공유 엔티티라(6.2.4), `recommendation_requests.user_id = 나`로 연결된 `course_id`를 역참조해 코스별 가장 최근 요청 시각(`MAX(created_at)`) 내림차순으로 반환한다.
- 응답 스키마는 7.3과 동일(`courses`/`next_cursor`). 커서는 `(requested_at, course_id)` 기준 keyset.
- 탈퇴(11.1) 후에는 `recommendation_requests.user_id`가 NULL로 비식별화(D-21)되므로 자연히 목록에서 사라진다.

### 7.4 POST /v1/courses/recommend — 코스 추천 (핵심)
> **로그인 필수(D-8)**. 비로그인 401 `UNAUTHORIZED`. **`station_id`는 선택값**(D-20) — 질의어에서 해석된 `location_mention`으로 서버가 resolve하며, resolve된 최종 역은 항상 정확히 1개(D-1). 하루 3회 무료(D-9). **코스는 단계(stage)별 복수 대안 구조(D-26)** — 사용자는 각 단계에서 대안 하나씩을 골라 자신만의 동선을 완성한다.
```json
// Request (1차 요청 — station_id 없이 질의어만)
{ "query": "게임 좋아하는 친구 3명과 홍대에서 밥먹고 놀다 술자리 예산은 인당 3만원!",
  "exclude_place_ids": [10293] }
```
```json
// Request (US-A4 추가 입력 Step 완료 후 재요청 — station_id/parsed_input 직접 전달)
{ "query": "게임 좋아하는 친구 3명과 밥먹고 놀다 술자리 예산은 인당 3만원!",
  "station_id": 239,
  "parsed_input": { "theme_tags": ["BOARD_GAME","FOOD","BAR"], "budget_tier": "30000_70000",
                     "companion_type": "FRIEND", "head_count": 4 },
  "exclude_place_ids": [] }
```
```json
// Response (200, 정상 생성)
{ "success": true,
  "data": {
    "course_id": 8821,
    "served_from": "LLM",
    "based_on_station": "합정",
    "search_radius_km": 5,
    "parsed_input": {
      "location_mention": "홍대",
      "theme_tags": ["BOARD_GAME","FOOD","BAR"],
      "budget_tier": "30000_70000",
      "companion_type": "FRIEND",
      "head_count": 4
    },
    "theme_tags": ["BOARD_GAME","FOOD","BAR"],
    "stages": [
      { "stage_order": 1, "stage_label": "저녁 식사", "options": [
          { "place_id": 10293, "name": "00식당", "category": "음식점", "price_range": "1만원대",
            "business_hours": { "mon": [["11:00","22:00"]], "sun": [] },
            "business_hours_text": "매일 11:00-22:00 (일 휴무)",
            "lat": 37.5491, "lng": 126.9140,
            "map_url": "https://map.kakao.com/link/map/P10293",
            "walking_distance_from_station_km": 0.4,
            "description": "넷이 앉기 좋은 가성비 한식집이에요." },
          { "place_id": 10310, "name": "00파스타", "category": "음식점", "price_range": "2만원대",
            "business_hours": null, "business_hours_text": null,
            "lat": 37.5488, "lng": 126.9155,
            "map_url": "https://map.kakao.com/link/map/P10310",
            "walking_distance_from_station_km": 0.6,
            "description": "분위기 좋은 이탈리안 레스토랑이에요." }
        ] },
      { "stage_order": 2, "stage_label": "보드게임", "options": [
          { "place_id": 10401, "name": "00보드게임카페", "category": "카페", "price_range": "1만원대",
            "business_hours_text": "매일 12:00-24:00",
            "lat": 37.5502, "lng": 126.9130,
            "map_url": "https://map.kakao.com/link/map/P10401",
            "walking_distance_from_station_km": 0.3,
            "description": "4인용 테이블과 최신 보드게임이 많아요." }
        ] }
    ],
    "similar_top_courses": [
      { "course_id": 5012, "theme_tags": ["BOARD_GAME","BAR"], "bayesian_score": 84.0, "rating_count": 27,
        "preview_places": ["00보드게임카페","00포차"], "total_walking_distance_km": 1.1 }
    ],
    "daily_remaining": 2,
    "disclaimer": "장소 정보는 최근 한 달 이내 기준이에요. 가격·영업시간은 변동될 수 있어 매장 확인을 권장드려요."
  }, "error": null }
```
```json
// Response (200, 위치/기타 필드 부족 — US-A4)
{ "status": "NEEDS_CLARIFICATION",
  "partial_parsed_input": { "theme_tags": ["BOARD_GAME","FOOD","BAR"], "head_count": 4 },
  "missing_fields": ["station_id", "budget_tier"] }
```
- `query` → LLM 분류(9장 2단계) → `location_mention` + `parsed_input`. 분류 불가 시 `INVALID_QUERY`, 필드 일부 부족 시 `NEEDS_CLARIFICATION`(US-A4).
- `location_mention`으로 역 resolve 실패(매칭되는 `stations` 없음) 시에도 하드 에러가 아니라 `NEEDS_CLARIFICATION`(`missing_fields: ["station_id"]`)로 전환된다.
- 생성 코스는 즉시 DB 저장·공개(D-10). `similar_top_courses`는 같은 역·겹치는 테마 중 베이지안 상위 N개(`recommend.similar_top_n=3`, D-13).
- `daily_remaining`: 오늘 남은 무료 생성 횟수(`ratelimit.user_daily` 기준). 멱등 재요청·`CACHE` 적중은 미차감(D-9).
- 한도 소진 시 `429 RATE_LIMIT_EXCEEDED`. **재추천(regenerate) API는 제거됨**(D-9) — 결과가 아쉬우면 질의어를 바꿔 다시 생성하거나 `exclude_place_ids`로 장소를 빼고 재생성(US-B3).

### 7.5 코스 리뷰 (점수 + 댓글 + 링크)
> 비로그인 허용(IP 해시로 식별). 점수는 0~100·5단위. 신원당 1리뷰(재요청 시 upsert).

```
POST /v1/courses/{course_id}/reviews        // 리뷰 등록/수정(upsert)
GET  /v1/courses/{course_id}/reviews?limit=20&cursor=   // 리뷰 목록(비로그인 열람)
DELETE /v1/courses/{course_id}/reviews/me    // 내(또는 내 IP) 리뷰 삭제
```
```json
// POST Request
{ "score": 85, "comment": "넷이서 놀기 딱 좋았어요. 술집은 예약 추천!",
  "links": ["https://blog.example.com/review/123", "https://map.kakao.com/link/map/P10293"] }
// POST Response
{ "success": true,
  "data": { "recorded": true, "review_id": 7782,
            "course_bayesian_score": 83.1, "rating_count": 39 }, "error": null }
```
```json
// GET Response
{ "success": true,
  "data": { "summary": { "bayesian_score": 83.1, "avg_score": 86.0, "rating_count": 39 },
            "reviews": [
              { "review_id": 7782, "score": 85, "comment": "넷이서 놀기 딱 좋았어요.",
                "links": ["https://blog.example.com/review/123"], "is_mine": true,
                "created_at": "2026-06-25T12:00:00+09:00" }
            ], "next_cursor": null }, "error": null }
```
- 점수가 5단위가 아니거나 0~100 범위를 벗어나면 `INVALID_PARAMETER`. 비로그인 IP 일일 상한 초과 시 `429`(`ratelimit.review_ip_daily`).
- 등록/수정/삭제 시 `courses.rating_count`/`rating_sum`/`bayesian_score`를 같은 트랜잭션에서 갱신(D-11).
- 리뷰 링크는 `rel="nofollow noopener"` 처리. 도메인 검사 없음(D-15).

```
POST /v1/courses/{course_id}/reviews/{review_id}/report    // 리뷰 신고 (D-15)
```
```json
// Request
{ "reason": "SPAM", "comment": "광고성 링크가 포함되어 있어요." }
// Response
{ "success": true, "data": { "recorded": true }, "error": null }
```
- 비로그인 허용(IP 기준). 동일 신원의 동일 리뷰 중복 신고는 `ON CONFLICT DO NOTHING`.
- 신고 누적이 `report.hide_threshold`(기본 5)를 넘으면 관리자 검토 대기. 자동 숨김은 V2(D-15/D-19).

### 7.6 POST /v1/courses/{course_id}/visit-survey — 사후 방문 설문 (P2)
```json
{ "visited": true }
```

### 7.6a POST /v1/places/{place_id}/report — 장소 정보 사용자 제보 (P1, v2.5)
> 비로그인 허용(IP 해시로 식별). 영업시간·별점·가격을 사용자가 직접 입력. **검증 없이 즉시 반영**(playwright 검증 파이프라인은 V2). 1인당 일일 상한 적용(`ratelimit.place_report_ip_daily`, 기본 10).
```json
// Request (모든 필드 선택)
{
  "business_hours": {
    "mon": [["11:00","22:00"]], "tue": [["11:00","22:00"]],
    "wed": [["11:00","22:00"]], "thu": [["11:00","22:00"]],
    "fri": [["11:00","23:00"]], "sat": [["12:00","23:00"]], "sun": []
  },
  "price_range": "1만원대",
  "rating": 4.5
}
// Response
{ "success": true,
  "data": { "recorded": true,
            "avg_rating": 4.2, "rating_count": 15 }, "error": null }
```
- `rating`: 1.0~5.0, 0.5단위. 위반 시 `INVALID_PARAMETER`.
- `rating` 제출 시 `places.user_rating_sum += rating × 2`(정수 저장), `user_rating_count += 1`. 표시용 `avg_rating = user_rating_sum / 2.0 / user_rating_count`.
- `business_hours` 제출 시 기존 값 **덮어쓰기**(last-write-wins). 악용 방지는 레이트리밋으로만(MVP).
- 동일 사용자(`ip_hash` 기준) 중복 제보는 `ON CONFLICT DO UPDATE`로 갱신(평점의 경우 이전 값 차감 후 재산출).

### 7.6b GET /v1/recommend/placeholder — 질의어 입력창 동적 placeholder
> 입력창에 띄울 예시 문구를 반환. 우선순위: 최근 질문(로그인) → 날씨/시간대 → 기본 예시(US-A3, D-17).
> **v2.6(D-20)**: 최초 화면엔 아직 확정된 역이 없으므로 `station_id`는 **선택값**이다. 미포함 시 서울 기본 좌표(시청 등)로 날씨를 조회한다. 로그인 사용자의 `home_station_id`가 있으면 그 좌표를 우선 사용.
```
GET /v1/recommend/placeholder
GET /v1/recommend/placeholder?station_id=239   // US-A4 폴백 등으로 역이 이미 확정된 경우
```
```json
{ "success": true,
  "data": { "placeholder": "퇴근하고 친구랑 가볍게 맥주 한잔 + 야경 좋은 곳!",
            "source": "WEATHER",
            "weather": { "condition": "CLEAR", "temp_c": 24 } }, "error": null }
```
- `source`: `RECENT`(사용자 최근 `query_text`) / `WEATHER` / `TIME` / `DEFAULT`. 비로그인은 `RECENT` 제외.
- **날씨 조회(D-17)**: 역 좌표로 OpenWeatherMap Current Weather API 호출(`units=metric`). 응답을 `app_config`(또는 별도 `weather_cache` DB 테이블)에 **30분 캐시**(`OPENWEATHER_CACHE_TTL_SEC`). 분류는 **기상 상태(State)** + **온도 구간(Temp tier)** 두 축의 조합으로 결정.

#### 온도 구간 (OWM `main.temp`, °C)
| tier | 범위 | 체감 |
|---|---|---|
| `VERY_HOT` | ≥ 33 | 폭염 — 너무 더워 |
| `HOT` | 26 ~ 32 | 더워 |
| `NICE` | 18 ~ 25 | 좋아 (쾌적) |
| `COOL` | 11 ~ 17 | 선선해 / 쌀쌀해 |
| `COLD` | 1 ~ 10 | 추워 |
| `VERY_COLD` | ≤ 0 | 꽁꽁 (영하) |

#### 기상 상태 (OWM `weather[0].main` + 보조 조건)
| state | OWM 값 | 보조 조건 | 체감 |
|---|---|---|---|
| `SUNNY` | `Clear` | — | 해가 쨍쨍 |
| `CLOUDY` | `Clouds` | — | 흐림 |
| `RAINY` | `Rain`, `Drizzle` | — | 비 온다 |
| `THUNDERSTORM` | `Thunderstorm` | — | 천둥번개 |
| `SNOWY` | `Snow` | — | 눈 온다 |
| `HUMID` | `Clouds`, `Clear` | `humidity ≥ 80%` + temp ≥ `HOT` | 습하고 더워 |
| `FOGGY` | `Mist`, `Fog`, `Haze` | — | 안개 / 뿌연 |

> `HUMID` 판정은 기상 상태보다 우선 적용(HOT·VERY_HOT 구간에서 습도 조건 충족 시 CLOUDY/SUNNY보다 HUMID를 선택).

#### 조합별 placeholder 문구
| state | temp tier | 예시 문구 |
|---|---|---|
| `SUNNY` | `VERY_HOT` | "폭염이에요 🥵 에어컨 빵빵한 실내에서 보드게임하고 냉면 먹기" |
| `SUNNY` | `HOT` | "더운 날은 실내로 시작! 보드게임카페에서 놀다가 저녁엔 야경 루프탑" |
| `SUNNY` | `NICE` | "날씨 너무 좋다! 야외 카페 테라스에서 브런치 + 공원 산책" |
| `SUNNY` | `COOL` | "선선하고 맑은 날, 야외 산책 + 감성 카페 한 바퀴" |
| `SUNNY` | `COLD` | "쌀쌀하지만 맑아요. 따뜻한 카페에서 수다 + 핫한 맛집" |
| `SUNNY` | `VERY_COLD` | "영하예요! 뜨끈한 국밥 + 실내 오락으로 몸 녹이기" |
| `CLOUDY` | `NICE` | "구름 낀 날씨, 전시관이나 영화관 어때요?" |
| `CLOUDY` | `COOL`·`COLD` | "흐린 날 카페에서 수다 떨다 맛집 탐방" |
| `CLOUDY` | `HOT`·`VERY_HOT` | "흐리고 더운 날, 시원한 실내에서 노래방 + 냉면" |
| `RAINY` | `NICE`·`HOT` | "비 오는 날은 실내가 최고! 보드게임 카페 + 맛있는 거 먹기" |
| `RAINY` | `COOL`·`COLD`·`VERY_COLD` | "비 오는 쌀쌀한 날, 따뜻한 실내에서 노래방 + 뜨끈한 국물 요리" |
| `THUNDERSTORM` | (전체) | "천둥번개 치는 날엔 실내 오락 풀코스! 보드게임 + 노래방 + 야식" |
| `SNOWY` | (전체) | "눈 오는 날, 분위기 있는 카페에서 수다 + 따뜻한 실내 오락" |
| `HUMID` | `HOT`·`VERY_HOT` | "후텁지근해요. 에어컨 빵빵한 실내에서 보드게임하고 시원한 거 먹기" |
| `FOGGY` | (전체) | "뿌연 날씨, 아늑한 카페에서 커피 한 잔 + 전시 관람" |

> 시간대 보조 분기(18시 이후 `EVENING`)는 `SUNNY`·`NICE`·`COOL`에 적용:
> - `SUNNY/NICE/EVENING` → "오늘 야경 예쁘겠다! 루프탑 가서 한잔하고 싶은 날"
> - 그 외 시간대는 위 테이블 기본 문구 사용.
>
> 조합에 해당하는 행이 없으면 `DEFAULT` 문구("오늘 어떤 하루를 보내고 싶으세요?")로 폴백.

- 날씨 API 실패 시 → `TIME` 기반 문구(아침/낮/저녁/밤)로 폴백, `source: "TIME"` 반환.
- 문구는 운영 초기 직접 조정 가능(13장 미해결 1번). 향후 `app_config` 또는 별도 설정 파일로 관리.

### 7.6c GET /v1/courses/{course_id} — 코스 상세 (SEO 공개 페이지, D-16)
> Next.js App Router SSR 페이지(`/courses/[id]`)의 데이터 소스. 비로그인 접근 가능. OG 태그·공유 링크 생성 기반.
```
GET /v1/courses/{course_id}
```
```json
{ "success": true,
  "data": {
    "course_id": 5012,
    "station_id": 239, "station_name": "합정",
    "theme_tags": ["BAR", "BOARD_GAME", "FOOD"],
    "budget_tier": "30000_70000", "companion_type": "FRIEND", "head_count": 4,
    "stages": [
      { "stage_order": 1, "stage_label": "저녁 식사", "options": [
          { "place_id": 10293, "name": "00식당", "category": "음식점",
            "price_range": "1만원대", "business_hours_text": "매일 11:00-22:00",
            "lat": 37.549, "lng": 126.913, "map_url": "...",
            "walking_distance_from_station_km": 0.4, "description": "..." }
        ] }
    ],
    "bayesian_score": 83.1, "avg_score": 86.0, "rating_count": 39,
    "created_at": "2026-06-25T12:00:00+09:00",
    "og": {
      "title": "합정역 친구 4명 | 보드게임 + 맛집 + 술집 코스",
      "description": "00식당 → 00보드게임카페 → 00포차 · ★ 86점",
      "image_url": "https://cdn.whatwedoin.app/og/courses/5012.png"
    }
  }, "error": null }
```
- **SSR(Next.js)**: `generateMetadata`에서 `og.*` 필드를 `<meta property="og:*">` 태그로 주입. 카카오톡·슬랙 등 링크 미리보기 지원.
- **공유 링크**: `https://{WEB_DOMAIN}/courses/{course_id}`. 링크/이미지 공유(D-16). 이미지 공유(OG 이미지 자동생성)는 V2.
- **신선도**: `stale_days` 초과 장소가 있으면 `is_stale: true` 배지. `CLOSED` 장소 포함 시 경고.

### 7.7 인증 엔드포인트
| Method | Path | 설명 |
|---|---|---|
| POST | `/v1/auth/kakao` | 카카오 code 검증 → JWT 발급 (유일 로그인 수단) |
| POST | `/v1/auth/refresh` | refresh 토큰으로 access 재발급 |
| POST | `/v1/auth/logout` | refresh 토큰 무효화 |
| GET | `/v1/users/me` | 내 회원정보 조회 |
| PATCH | `/v1/users/me` | 회원정보 수정(선택 항목) |
| DELETE | `/v1/users/me` | 회원 탈퇴(WITHDRAWN) |

```json
// POST /v1/auth/kakao — Request ({WEB_DOMAIN} 등은 12장 설정값 참조)
{ "authorization_code": "abc123...", "redirect_uri": "https://{WEB_DOMAIN}/oauth/callback" }
// Response (200)
{ "success": true,
  "data": { "access_token": "eyJ...", "refresh_token": "eyJ...", "is_new_user": true,
            "user": { "id": 1024, "nickname": "도현", "preferred_companion_type": null } }, "error": null }
```

---

## 8. 인증 / OAuth 플로우 (카카오 단일)

```
[클라이언트]                [WhatWeDoin API]             [카카오]
    │ 1. 카카오 로그인 SDK 실행 │                          │
    │ ─────────────────────────────────────────────────► │
    │ 2. authorization code ◄───────────────────────────  │
    │ 3. POST /auth/kakao (code) ─►│ 4. code→token 교환,   │
    │                              │    프로필 조회 ─────► │
    │                              │ ◄── 프로필(oauth_id)  │
    │                              │ 5. users upsert       │
    │ 6. 자체 JWT(access/refresh) ◄│                       │
```
- 클라이언트는 authorization code만 확보. **토큰 교환·프로필 조회는 백엔드에서만**(시크릿 미노출).
- 최초 로그인이면 `users` 신규 생성 + 약관 동의(온보딩), 기존 회원이면 바로 JWT 발급.

---

## 9. 추천 엔진 내부 시퀀스 (recommend 처리)

```
0. 인증 검사: 로그인 필수(없으면 401 UNAUTHORIZED), 종료                         [D-8]
   멱등성 검사: Idempotency-Key 동일 → 저장된 이전 결과 반환(LLM 미호출·한도 미차감), 종료
1. 입력 검증 + 한도: query 비어있지 않음(station_id는 선택값, D-20).
   일일 생성 횟수 COUNT(recommendation_requests, served_from=LLM, 오늘 KST) < ratelimit.user_daily(=3), 초과 시 429  [D-9]
2. 질의어 분류(LLM, 저비용 모델): query → parsed_input
   { location_mention, theme_tags[], budget_tier, companion_type, head_count }   [D-8, D-20]
   └ 분류 결과 빈 항목은 사용자 preferred_*/home_station_id 로 보정
   └ 그래도 비는 필드(station_id 포함)가 있으면 → NEEDS_CLARIFICATION(200) 반환, LLM 미호출·한도 미차감, 종료 (US-A4)
   └ 서비스 무관/분류 불가 → INVALID_QUERY, 종료
2.5 위치 해석(신규, D-20): req.station_id가 이미 주어졌으면(US-A4 재요청) 그대로 사용.
    아니면 location_mention으로 stations 테이블 이름 매칭 → station_id resolve.
    └ 매칭 실패 → missing_fields=["station_id"]로 NEEDS_CLARIFICATION(200), 종료 (US-A3a/US-A4)
3. 캐시 조회(DB): key = hash(station_id + 정규화 parsed_input) → `course_cache` 테이블 조회
   └ 히트 → 캐시 반환(served_from=CACHE, 한도 미차감), 단 7단계 유사 코스는 최신 조회, 종료
4. 후보 장소 조회: PostGIS ST_DWithin로 역 5km 반경 + theme_tags/budget 필터 (F-01)
   └ exclude_place_ids 제외 (F-04, US-B3)
   └ 부족 시 반경 7km로 1회 확장 → 여전히 부족 → NO_COURSE_FOUND
5. LLM 호출(고급 모델): 검증 후보 풀 내에서만 조합·동선·설명 생성 (F-02, F-15)
   └ 후보 풀 place_id 화이트리스트 전달(structured output)
5.5 LLM 출력 검증(환각 방지): 반환 place_id ∈ 후보 풀 확인
   └ 위반 시 제거 후 1회 재요청, 실패 시 NO_COURSE_FOUND
6. 영속화: content_hash 산출 → courses UPSERT(ON CONFLICT) → course_id            [D-10]
   - courses.places 스냅샷 + course_places 정규화 행 동시 적재(생성 즉시 공개)
   - 캐시 저장(TTL 2주), recommendation_requests 로깅(served_from=LLM, idempotency_key)
   - 일일 생성 카운트 +1
7. 유사 테마 고득점 코스 조회:                                                    [D-13]
   WHERE station_id=? AND theme_tags && parsed_input.theme_tags AND course_id<>새코스
   ORDER BY bayesian_score DESC LIMIT recommend.similar_top_n(=3)
8. 응답: 새 코스 + similar_top_courses + parsed_input + daily_remaining + disclaimer
```
> **비용 통제**: 0·3단계에서 LLM 미호출 경로 확보. 2단계는 저비용 모델(분류), 5단계만 고급 모델(톤 생성)로 단계적 전략.
> **관찰성(Langfuse)**: 2·5단계 LLM 호출을 trace로 감싸 프롬프트·토큰·모델별 비용·지연 기록. 개인식별정보·질의어 원문 위치 미포함.

---

## 10. 공통 에러 코드

| HTTP | code | 설명 |
|---|---|---|
| 400 | `INVALID_PARAMETER` | 필수 파라미터 누락/형식 오류 (`query` 공백, 점수 5단위·범위 위반 등) |
| 400 | `INVALID_QUERY` | 질의어를 코스 조건으로 분류할 수 없음(서비스 무관/모호) |
| 401 | `UNAUTHORIZED` | 토큰 누락/만료. **추천 생성은 로그인 필수**(D-8) |
| 404 | `STATION_NOT_SUPPORTED` | 미지원 역 |
| 404 | `NO_COURSE_FOUND` | 조건 부합 후보 없음(Cold Start) |
| 429 | `RATE_LIMIT_EXCEEDED` | 일일 무료 생성 횟수 초과(user, `ratelimit.user_daily`) 또는 비로그인 리뷰 IP 상한 초과 |
| 503 | `UPSTREAM_UNAVAILABLE` | 외부 지도/플레이스 API 장애 |
| 503 | `LLM_UNAVAILABLE` | Claude API 실패/타임아웃(유사 코스 제안·재시도 권장, 한도 미차감) |

> **에러 아님(200)**: `NEEDS_CLARIFICATION` — 질의어 분류 결과 중 `station_id` 등 필수 필드가 비었을 때(US-A4, D-20). `missing_fields[]`/`partial_parsed_input`을 담아 200으로 반환하며, LLM 코스 생성은 호출되지 않고 일일 한도도 차감되지 않는다.
> **삭제(D-1)**: `TOO_MANY_STATIONS`, `STATION_TOO_FAR`는 단일 역 정책으로 제거.
> **삭제(D-20)**: 구 `NO_STATION`/`STATION_NOT_FOUND`류 하드 에러는 `NEEDS_CLARIFICATION` 폴백으로 대체.
> **삭제(D-9)**: regenerate·`served_from=SAVED_LIST` 관련 분기 제거. 멱등키 재요청은 에러가 아니라 이전 결과를 200으로 반환(한도 미차감).

---

## 11. 보안 / 개인정보 체크리스트

- 토큰 교환·클라이언트 시크릿은 **서버에서만** 처리, 클라이언트 미노출.
- JWT: access 단기(30분) + refresh 회전(rotation), refresh는 DB 저장/무효화(6.2.11). 재사용 감지 시 전 토큰 폐기.
- 성별·출생연도 등 개인정보: 수집 목적 고지 + 분리 동의, 선택 입력, 미입력 허용.
- 저장 공개 코스는 생성자 비식별.
- 위치는 GPS 자동 수집 미사용. 질의어 텍스트 안의 지명·동네 언급을 LLM이 해석하거나(D-20, 주 경로), 그마저 없으면 US-A4 추가 입력 Step의 지도 탭/역 검색(폴백)으로 사용자가 직접 선택한다. 위치 정보는 URL 파라미터 미포함.
- 비로그인 리뷰 식별 IP는 **해시/마스킹(`ip_hash`)만 저장**하고 원문 IP는 장기 저장 금지. 리뷰 레이트리밋 키도 `ip_hash` 사용.
- 질의어(`query_text`)는 비식별 코스 스냅샷으로만 보관하며 개인식별정보 결합 금지. LLM 트레이스(Langfuse)에 개인식별정보·질의어 원문 위치 미포함.

### 11.1 탈퇴 시 개인정보 파기/익명화 (PIPA)
- `DELETE /v1/users/me` → `status=WITHDRAWN`과 **동시에** 개인정보 컬럼 파기/익명화: `nickname`·`profile_image_url`·`email` 삭제, `gender/birth_year/dating_stage`·`oauth_id` 제거/비식별화.
- `course_reviews`/`recommendation_requests`의 `user_id`는 통계 보존 필요 시 **익명화**(NULL). 두 컬럼 모두 nullable(D-21 — `recommendation_requests.user_id`는 원래 D-8로 NOT NULL이었으나 본 익명화를 위해 완화). `course_reviews.chk_review_identity`(user_id/ip_hash 중 하나 필수) CHECK도 같은 이유로 제거(D-22) — 로그인 리뷰는 `ip_hash`가 원래 없어 `user_id`까지 비우면 위반되던 문제. 리뷰 본문(댓글·링크)은 보존 정책에 따라 익명 처리.
- DB `refresh_tokens`에서 해당 `user_id` 레코드 일괄 폐기(revoked_at 설정).

### 11.2 외부 데이터 수집의 법적 리스크 (⚠️ 출시 전 필수, US-F4)

> **v2.5 범위 확정**: 카카오 로컬 REST API 기본 메타(이름·주소·카테고리·좌표·전화번호) 사용은 공식 API 이용약관 허용 범위 — **SCRUM-70 법무 게이트 대상 아님**. **게이트 대상은 크롤링(상세 페이지·영업시간·가격·이미지 스크래핑)에만 해당.**

- **API 사용(MVP, 법무 게이트 불필요)**: 카카오 로컬 REST API를 통한 기본 메타 수집·캐싱. 이용약관 내 허용 범위이므로 SCRUM-70 차단 없이 진행 가능.
- **크롤링(법무 게이트 필요)**: 카카오맵 상세 페이지 등 웹 크롤링은 약관·저작권·DB권 침해 소지. 크롤링 도입 시 법무 선행 검토 필수(SCRUM-70 트리거).
- 완화: ① API 허용 범위 사용 우선 ② 영업시간·가격·평점은 **사용자 직접 제보**(`POST /v1/places/{id}/report`)로 대체(v2.5, 크롤링 불필요) ③ 크롤링 도입 전 반드시 법무 확인 + 출처 표기·갱신 정책 문서화.
- **현재 MVP 상태**: API 기반 ETL + 사용자 제보 조합 → 크롤링 없이 운영 가능. SCRUM-70은 크롤링 도입 결정 시 재활성화.

---

## 12. 설정값 / 시크릿 (운영자 직접 입력)

> PRD 플레이스홀더(`{...}`)에 대응하는, **운영자가 직접 결정·발급해야 하는 값** 모음.
> 비밀값(시크릿)은 이 문서에 **평문 저장하지 말고** AWS Secrets Manager / SSM Parameter Store에 보관하고, 여기엔 "어디서 발급받는지"만 적는다.
> 표기: `TODO` = 미정/직접 입력, `(secret)` = 비밀값(코드·git에 커밋 금지).

### 12.1 도메인 / URL
| 키 | 설명 | 값 |
|---|---|---|
| `WEB_DOMAIN` | 웹 서비스 도메인 (예: `whatwedoin.app`) | `TODO` |
| `API_DOMAIN` | 백엔드 API 도메인 (예: `api.whatwedoin.app`) | `TODO` |
| `WEB_OAUTH_CALLBACK` | OAuth 콜백 = `https://{WEB_DOMAIN}/oauth/callback` | `TODO` |
| `CORS_ALLOWED_ORIGINS` | API가 허용할 프론트 오리진 | `https://{WEB_DOMAIN}` |

### 12.2 OAuth (카카오 단일)
> 카카오 개발자 콘솔(https://developers.kakao.com)에서 앱 등록 후 발급. Redirect URI는 `WEB_OAUTH_CALLBACK`을 콘솔에 등록해야 동작.

| 키 | 설명 | 값 |
|---|---|---|
| `KAKAO_REST_API_KEY` | REST API 키 | `TODO` |
| `KAKAO_CLIENT_SECRET` | 보안 → Client Secret | `(secret)` |
| `KAKAO_REDIRECT_URI` | 등록한 Redirect URI | `= WEB_OAUTH_CALLBACK` |
| `KAKAO_JS_KEY` | 웹 로그인/맵 JS SDK 키 | `TODO` |

> 네이버 등 타 인증수단은 미사용(MVP).

### 12.3 지도 / 장소 데이터 소스
| 키 | 설명 | 값 |
|---|---|---|
| `KAKAO_MAP_JS_KEY` | 카카오맵 JS SDK 키 (지도 렌더링) | `TODO` |
| `KAKAO_LOCAL_REST_KEY` | 카카오 로컬(플레이스) REST 키 (장소 메타 수집) | `(secret)` |
| `NAVER_MAP_CLIENT_ID` | (보류) 네이버 지도 Client ID | `TODO` |
| `NAVER_MAP_CLIENT_SECRET` | (보류) 네이버 지도 Client Secret | `(secret)` |
| `OPENWEATHER_API_KEY` | OpenWeatherMap Current Weather API 키(7.6b, D-17). 무료 티어 60 call/min. | `(secret)` |
| `OPENWEATHER_CACHE_TTL_SEC` | 날씨 캐시 TTL(초). 기본 1800(30분). | `1800` |

#### 12.3.1 크롤링 보강 파이프라인 (영업시간·가격 등 API 미제공 항목)
| 키 | 설명 | 값 |
|---|---|---|
| `CRAWLER_USER_AGENT` | 크롤러 식별 User-Agent | `TODO` |
| `CRAWLER_RATE_LIMIT_RPS` | 초당 요청 제한 | `1` |
| `CRAWLER_TARGET_SOURCES` | 보강 대상 사이트 목록 | `TODO` |
| `CRAWLER_SYNC_CRON` | 신선도 갱신 배치 주기 | `TODO` (예: `0 4 * * *`) |

> **법무·운영 주의**: 크롤링은 `robots.txt`·이용약관 준수, 레이트 제한 필수. 상업적 재사용 범위는 출시 전 법무 검토(11.2). 카카오 로컬 API 무료 쿼터 초과 시 유료 전환 또는 캐시 TTL 연장으로 호출량 통제.

### 12.4 LLM (Anthropic Claude — 기본 공급자)
| 키 | 설명 | 값 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API 키 (https://console.anthropic.com) | `(secret)` |
| `LLM_PROVIDER` | LLM 공급자 선택 | `anthropic` |
| `LLM_MODEL_PRIMARY` | 코스 톤·동선 생성 모델(9장 5단계) | `claude-sonnet-4-6` |
| `LLM_MODEL_CLASSIFIER` | 질의어 분류(저비용) 모델(9장 2단계) | `claude-haiku-4-5-20251001` |

#### 12.4.1 LLM Provider 추상화 인터페이스

> **설계 원칙**: LLM 호출은 직접 SDK를 호출하지 않고 **Provider 추상화 인터페이스**를 경유한다. 인터페이스는 `generate(prompt, model, params) → response` 형태로 정의하고, Anthropic/OpenAI 등 공급자별 구현체를 교체 가능하도록 설계(Spring AI 패턴 참조). 공급자 전환 시 인터페이스 구현체만 교체하면 되고 비즈니스 로직(9장 시퀀스)은 변경 없음.
>
> | 환경변수 | 설명 | 값 |
> |---|---|---|
> | `LLM_PROVIDER` | 사용할 LLM 공급자 | `anthropic`(기본) / `openai` |
> | `LLM_MODEL_PRIMARY` | 코스 생성 모델(공급자별 모델명으로 매핑) | `claude-sonnet-4-6` |
> | `LLM_MODEL_CLASSIFIER` | 질의어 분류 모델 | `claude-haiku-4-5-20251001` |

#### 12.4.2 LLM Observability (Langfuse)
| 키 | 설명 | 값 |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | `TODO` |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | `(secret)` |
| `LANGFUSE_HOST` | Langfuse 엔드포인트 | `https://cloud.langfuse.com` |

### 12.5 인증 / JWT
| 키 | 설명 | 값 |
|---|---|---|
| `JWT_SECRET` | JWT 서명 키 (256bit+ 랜덤) | `(secret)` |
| `JWT_ACCESS_TTL` | access 토큰 만료 | `30m` |
| `JWT_REFRESH_TTL` | refresh 토큰 만료 | `14d` |

### 12.6 AWS / Terraform 변수
> `terraform/`의 `*.tfvars`에 입력. 리전은 서울 고정.

| 키 | 설명 | 값 |
|---|---|---|
| `aws_region` | 리전 | `ap-northeast-2` |
| `aws_account_id` | AWS 계정 ID | `TODO` |
| `project_name` | 리소스 네이밍 prefix | `whatwedoin` |
| `environment` | 환경 (`dev`/`prod`) | `TODO` |
| `vpc_cidr` | VPC CIDR | `10.0.0.0/16` |
| `ecr_repository` | 백엔드 ECR 리포지토리명 | `whatwedoin-api` |
| `ecs_cluster_name` | ECS 클러스터명 | `whatwedoin-cluster` |
| `ecs_task_cpu` / `ecs_task_memory` | Fargate 태스크 스펙 | `512` / `1024` |
| `rds_instance_class` | RDS 인스턴스 타입 | `db.t4g.micro` (dev) |
| `rds_db_name` | DB 이름 | `whatwedoin` |
| `rds_username` | DB 마스터 유저 | `TODO` |
| `rds_password` | DB 마스터 비밀번호 | `(secret)` |
| `acm_certificate_arn` | ALB TLS 인증서 ARN | `TODO` |
| `route53_zone_id` | 도메인 호스팅 영역 ID | `TODO` |

### 12.7 시크릿 보관 위치
- **백엔드 런타임 시크릿**(`*_SECRET`, `*_API_KEY`, `JWT_SECRET`, DB 비밀번호) → **AWS Secrets Manager**, ECS Task Definition `secrets`로 주입.
- **Terraform 백엔드 상태** → S3 버킷 + DynamoDB 잠금 테이블(`TODO`: 버킷명/테이블명).
- **로컬 개발** → `.env.local`(git ignore). 절대 커밋 금지.

> 이 문서에 `(secret)` 실값을 적지 말 것. "발급처/보관 위치"만 기록.

## 13. 미해결 결정 (Open Questions)

> 대부분 v2.0·v2.1에서 해소됨. **현재 미결 항목만 기재.**

1. **날씨 문구 세부 조정**: 7.6b 조합 테이블의 예시 문구는 운영 초기 실측 반응에 따라 직접 수정. 분류 기준(온도 경계·습도 임계치)도 동일하게 조정 가능.

> NFR(4장) 수치는 현행 가정값으로 확정 진행. KPI(1.4장)는 별도 수정 완료.

---

> **v2.0에서 해소된 결정**: 무료 재추천(D-9) · plan_type 폐기→통제 enum 테마(D-12·D-14) · companion_type 4종(D-7) · 피드백→통합 리뷰(D-11) · 코스 즉시 공개(D-10).
> **v2.1(2026-06-25)에서 해소된 결정**: 베이지안 사전값 prior_mean=50/prior_count=5(D-18) · 테마 enum 12종 확정(D-14) · 리뷰 링크 안전성 검사 제거+신고 기능 추가(D-15) · IP 추가 방어 V2(D-19) · 날씨 API OpenWeatherMap·역 좌표 기반(D-17) · SEO 공개 페이지 연계(D-16).
> **v2.3(2026-06-25)에서 해소된 결정**: Redis/ElastiCache 제거 → 캐시·레이트리밋·refresh 토큰 모두 PostgreSQL로 통합. AWS 인프라 ECS+RDS만 유지.
