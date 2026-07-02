# WhatWeDoin

"오늘 뭐하고 놀지?" AI가 지하철역 기반으로 놀거리 코스를 즉시 추천해주는 서비스.

> Z세대 타겟. 지도나 역 선택 없이 **한 문장 질의어**만 입력하면 AI가 문장 속 지명·동네를 읽어 가장 가까운 지하철역을 자동으로 잡고, 동선이 짜인 플랜을 즉시 생성한다. 비로그인으로도 코스 열람·탐색·리뷰가 전부 가능하고, AI 생성(하루 3회 무료)만 로그인이 필요하다.

전체 요구사항은 [`prd.md`](./prd.md) 참고.

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 (App Router, TypeScript, React 19) |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.x (async, asyncpg) |
| DB | PostgreSQL 16 + PostGIS (AWS RDS) |
| LLM | Claude API(Anthropic) / Gemini — Provider 추상화로 전환 가능 |
| 지도 | 카카오맵 JS SDK |
| 인증 | 카카오 OAuth 2.0 + 자체 JWT (access 30분, refresh 14일 회전·재사용 탐지) |
| API 문서 | 손으로 작성한 OpenAPI 3.0 명세(`backend/openapi.yaml`)를 Swagger UI(`/docs`)가 서빙 |
| IaC | Terraform (AWS ECS Fargate + RDS + ALB + CloudFront, 서울 리전) |
| CI/CD | GitHub Actions (OIDC → ECR/ECS, S3+CloudFront) |

---

## 로컬 개발

### 사전 준비

```bash
cp .env.example .env
# ANTHROPIC_API_KEY(또는 GEMINI_API_KEY), KAKAO_REST_API_KEY 등 필수 값 입력
```

### ① DB 기동

```bash
docker compose up -d
docker compose ps   # db healthy 확인
```

### ② Backend 기동

```bash
cd backend
cp .env.example .env
docker compose up
# http://localhost:8080/health → 200
# http://localhost:8080/docs   → Swagger UI (openapi.yaml 기반)
```

### ③ Frontend 기동

```bash
cd frontend
cp .env.example .env.local
npm run dev         # 또는 docker compose up
# http://localhost:3000
```

### 스키마 재생성

```bash
docker compose down -v && docker compose up -d
```

### DB 마이그레이션

```bash
cd backend
alembic upgrade head
```

### 데이터 시딩

```bash
cd backend
python scripts/seed_stations.py             # 역 + 노선 시딩
python scripts/etl_places.py                # 카카오 로컬 API 장소 수집
python scripts/backfill_place_theme_tags.py # 미분류 places.theme_tags 일괄 재분류
python scripts/etl_menu_keywords.py         # 메뉴 키워드 커버리지 보강(선택)
```

### 테스트

```bash
cd backend && uv run pytest     # 160+ 테스트
cd frontend && npm test         # Jest + React Testing Library
cd frontend && npx tsc --noEmit # 타입 체크
```

---

## 핵심 사용자 플로우

```
메인 화면 — 역 선택 UI 없음. "어떻게 놀고 싶어?" 질의어 입력창 하나만 존재.
  예) "홍대에서 친구랑 술 한잔하고 싶어"
        ↓
AI가 질의어에서 위치(동네·지명) + 테마 + 예산 + 동행 + 인원을 한 번에 분류
  → 지명이 매칭되면 최근접 지원 역으로 자동 resolve
  → 위치·필수 정보가 부족하면 ClarificationStep(역 검색 폴백 등)으로 보완 요청
        ↓
해석된 역 반경(5km→필요 시 7km 확장) 후보 장소로 2~4단계 코스 생성
  (단일 카테고리 요청은 1단계도 허용, 메뉴 키워드 언급 시 이름 일치 후보 우선)
        ↓
결과 화면: 단계별 타임라인 + 카카오맵 + 유사 테마 인기 코스 3개 동반 노출
        ↓
100점·5단위 점수 + 댓글 + 링크로 리뷰 → 베이지안 평균으로 메인 랭킹 반영
```

---

## 디렉토리 구조

```
WhatWeDoin/
├── frontend/                   # Next.js (App Router, TypeScript)
│   └── src/
│       ├── app/
│       │   ├── page.tsx                  # 홈 — 질의어 입력 하나만 (역 선택 UI 없음, D-20)
│       │   ├── result/page.tsx           # 추천 결과 (SSR shell) + loading.tsx (스켈레톤)
│       │   ├── courses/page.tsx          # 코스 탐색 (필터 + 무한스크롤)
│       │   ├── courses/[course_id]/page.tsx # 코스 상세 (OG 태그 + 카카오맵)
│       │   ├── courses/mine/page.tsx     # 내가 생성한 코스 모아보기
│       │   ├── auth/callback/page.tsx    # 카카오 OAuth 콜백
│       │   └── onboarding/page.tsx       # 약관 동의 + 개인화 온보딩
│       ├── components/
│       │   ├── ResultClient.tsx / ResultPageClient.tsx  # 추천 요청·NEEDS_CLARIFICATION 처리
│       │   ├── ClarificationStep.tsx     # 위치·예산 등 추가 입력 Step (US-A4, 역 검색 폴백)
│       │   ├── CourseTimeline.tsx        # 단계별 코스 타임라인
│       │   ├── CourseCard.tsx / PlaceCard.tsx  # 코스/장소 카드
│       │   ├── CourseMap.tsx / KakaoMap.tsx    # 카카오맵 렌더링
│       │   ├── SimilarCourses.tsx        # 유사 테마 고득점 코스 3개
│       │   ├── ReviewSection.tsx / ReviewForm.tsx  # 리뷰 목록·작성(점수 슬라이더+댓글+링크)
│       │   ├── StationSearch.tsx         # 역 이름 자동완성(ClarificationStep 폴백용)
│       │   ├── LoginButton.tsx / LoginGateModal.tsx  # 카카오 로그인 + 로그인 유도 모달
│       │   ├── QuotaBadge.tsx            # 일일 잔여 생성 횟수 배지
│       │   ├── ThemeToggle.tsx           # 라이트/다크 테마 전환
│       │   ├── ErrorFallback.tsx         # 에러 유형별(401/429/503 등) 안내
│       │   ├── DeleteAccountModal.tsx    # 탈퇴 확인 모달
│       │   └── ReportBottomSheet.tsx     # 장소 정보(영업시간·별점·가격) 제보
│       ├── hooks/useDynamicPlaceholder.ts# 날씨·시간대·최근 질문 기반 placeholder 순환
│       └── lib/
│           ├── api.ts          # API 클라이언트 전체
│           ├── auth.ts         # JWT 저장·자동 갱신·로그아웃
│           ├── quota.ts        # 일일 잔여 횟수 로컬 캐시
│           ├── theme.ts        # 라이트/다크 테마 상태
│           └── enumOptions.ts  # enum 코드 ↔ 한국어 라벨 매핑(D-24)
├── backend/                     # FastAPI
│   ├── app/
│   │   ├── core/                # config · 비동기 DB 세션 · auth deps
│   │   ├── routers/              # auth · users · stations · courses · reviews · recommend · places · health
│   │   ├── models/               # SQLAlchemy 모델 + enums + 카테고리 라벨
│   │   └── services/
│   │       ├── llm/                    # LLM Provider 추상화 (Anthropic / Gemini)
│   │       ├── auth.py                 # 카카오 OAuth + JWT 발급/회전
│   │       ├── cache_ratelimit.py       # 결과 캐시·멱등키·일일 한도 (PostgreSQL, Redis 없음)
│   │       ├── classifier.py           # 질의어 → location_mention/theme_tags/budget/companion/menu_keyword
│   │       ├── course_generator.py     # LLM 코스 생성 + 환각 검증 + 재시도(지수 백오프)
│   │       ├── place_search.py         # PostGIS 반경 검색 + 메뉴 키워드 우선순위/실시간 보강
│   │       ├── kakao_places.py         # 카카오 로컬 REST API (ETL + 실시간 키워드 검색)
│   │       └── weather.py              # OpenWeatherMap 현재 날씨(placeholder용)
│   ├── openapi.yaml         # 손으로 작성한 OpenAPI 3.0 명세 — /docs가 이 파일을 서빙
│   ├── alembic/             # DB 마이그레이션
│   ├── scripts/             # seed_stations · etl_places · backfill_place_theme_tags · etl_menu_keywords
│   └── tests/               # pytest 160+ 종
├── docker-compose.yml       # 루트 (PostgreSQL + PostGIS)
├── terraform/               # AWS IaC (VPC · ECS · RDS · ALB · CloudFront)
└── .github/workflows/       # CI(PR) · deploy-backend · deploy-frontend
```

---

## 구현 순서 및 진척도

> **전체 진척도: 약 97%** (Phase 1~6 완료, Phase 7 인프라 진행 중)

### Phase 1 — 기반 구축 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | PostgreSQL + PostGIS DB 스키마 + Alembic 마이그레이션 | SCRUM-66 |
| ✅ | FastAPI 기본 구조 (`health`, `config`, async DB 세션) | SCRUM-65 |
| ✅ | 역 데이터 시딩 (`stations` + `station_lines` upsert) | SCRUM-73 |
| ✅ | 장소 ETL (카카오 로컬 REST API → `places` 적재) | SCRUM-72 |
| ✅ | `places.theme_tags` 컬럼 추가 + 카카오 카테고리 → enum 매핑 + 백필 스크립트 | SCRUM-72, SCRUM-96 |
| ✅ | LLM Provider 추상화 인터페이스 (Anthropic / Gemini 구현체) | SCRUM-71 |
| ✅ | 장소 정보 사용자 제보 API (`POST /v1/places/{id}/report`) | SCRUM-74 |

### Phase 2 — AI 추천 엔진 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | LLM 질의어 분류기 — 위치(`location_mention`)·`theme_tags`·`budget_tier`·`companion_type`·`head_count`·`menu_keyword` 추출 | SCRUM-37 |
| ✅ | 질의어 속 지명·동네를 최근접 지원 역으로 자동 resolve (역 선택 UI 제거, D-20) | SCRUM-60 이후 |
| ✅ | PostGIS `ST_DWithin` 후보 장소 검색 (5km → 7km 확장) | SCRUM-38 |
| ✅ | 메뉴 키워드 후보 우선순위 + 커버리지 부족 시 실시간 카카오 키워드 검색 보강 | SCRUM-97, SCRUM-98 |
| ✅ | LLM 코스 생성(단계별 복수 대안) + 환각 검증(후보 외 place_id/중복 제거·재시도) | SCRUM-38, D-26 |
| ✅ | 단일 카테고리 요청 시 1단계 코스 생성 허용 | SCRUM-95 |
| ✅ | 추천 오케스트레이터 (`POST /v1/courses/recommend`) | SCRUM-36 |
| ✅ | 일일 한도 3회 + 멱등키(`Idempotency-Key`) + 결과 캐시 (PostgreSQL, Redis 없음) | SCRUM-39, SCRUM-92 |
| ✅ | LLM 장애 시 지수 백오프 재시도 + 503 `LLM_UNAVAILABLE` 폴백 코스 | SCRUM-43 |
| ✅ | 동적 Placeholder API (날씨·시간대·최근 질의어) | SCRUM-34 |

### Phase 3 — 프론트엔드 핵심 UI ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | 홈 화면 — 질의어 입력창 하나 + 동적 placeholder (역 선택 UI 없음) | SCRUM-45, D-20 |
| ✅ | NEEDS_CLARIFICATION 추가 입력 Step (역 검색 폴백 등, `ClarificationStep`) | US-A4 |
| ✅ | 코스 결과 타임라인 UI + 장소 카드 + 카카오맵 | SCRUM-45, SCRUM-94 |
| ✅ | 장소 제외 선택 및 재생성 버튼 UI | SCRUM-41 |
| ✅ | 로딩 스켈레톤 shimmer + SVG 스피너 | SCRUM-35 |
| ✅ | 에러 유형별 안내 UI (401/429/503/기타) | SCRUM-42 |
| ✅ | 동적 Placeholder 순환 훅 (`useDynamicPlaceholder`) | SCRUM-33 |
| ✅ | 장소 정보 제보 바텀시트 | SCRUM-74 |
| ✅ | 라이트/다크 테마 전환 + 데스크탑 반응형 레이아웃 | 별도 |

### Phase 4 — 인증 & 사용자 관리 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | 카카오 OAuth → 자체 JWT 발급 (`POST /v1/auth/kakao`) | SCRUM-52 |
| ✅ | 토큰 갱신·로그아웃 (`/auth/refresh`, `/auth/logout`, refresh 회전+재사용 탐지) | SCRUM-52 |
| ✅ | 마이페이지 (`GET/PATCH /v1/users/me`) | SCRUM-54 |
| ✅ | 회원 탈퇴 + PIPA 익명화 (`DELETE /v1/users/me`) | SCRUM-25 |
| ✅ | 로그아웃 시 일일 한도 카운트가 초기화되던 버그 수정 | SCRUM-88 |
| ✅ | 프론트: 카카오 로그인 버튼 + `/auth/callback` + JWT 관리 | SCRUM-51 |
| ✅ | 프론트: 온보딩 약관 동의 + 개인화 입력 2단계 | SCRUM-53 |
| ✅ | 프론트: 탈퇴 확인 모달 + 드롭다운 메뉴 | SCRUM-55 |

### Phase 5 — 코스 탐색 & 리뷰 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | 코스 목록 API (`GET /v1/courses`) — 필터 + 커서 페이지네이션 | SCRUM-50 |
| ✅ | 내가 생성한 코스 API (`GET /v1/users/me/courses`) | D-25 |
| ✅ | 코스 상세 API (`GET /v1/courses/{id}`) — OG 태그 포함 | SCRUM-46 |
| ✅ | 코스 리뷰 API (`POST/GET/DELETE`) — 베이지안 평균 갱신 | SCRUM-48 |
| ❌ | ~~리뷰 신고 API~~ — 미사용 죽은 코드로 확인되어 삭제 | SCRUM-91, D-27 |
| ✅ | 프론트: 코스 탐색 페이지 (`/courses`, 필터 + 무한스크롤) | SCRUM-49 |
| ✅ | 프론트: 코스 상세 페이지 (`/courses/[course_id]`) — 카카오맵·평점·운영시간 | SCRUM-40, SCRUM-89, SCRUM-94 |
| ✅ | 프론트: 리뷰 작성 UI (100점·5단위 슬라이더 + 댓글 + 링크) | SCRUM-47 |
| ✅ | 프론트: 리뷰 목록 + 내 리뷰 삭제 | SCRUM-47 |
| ✅ | 프론트: 내가 생성한 코스 모아보기 페이지 (`/courses/mine`) | D-25 |

### Phase 6 — 역 검색 & 고도화 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | 역 목록/단일 조회 API (`GET /v1/stations`, `/v1/stations/{id}`) — bounds 필터 + 노선 조인 | SCRUM-30 |
| ✅ | 역 검색 API (`GET /v1/stations/search`) — 자동완성 | SCRUM-32 |
| ✅ | 프론트: 역 이름 자동완성 (`StationSearch`, ClarificationStep 폴백에서 사용) | SCRUM-31 |
| ✅ | 프론트: 유사 테마 고득점 코스 3개 동반 노출 | SCRUM-40 |
| ✅ | 프론트: 일일 잔여 횟수 배지 (`QuotaBadge`, KST 기준) | SCRUM-44 |
| 🔲 | 신선도 배치 (월 1회 재동기화) | P1 |

### Phase 7 — 인프라 & 배포 ⚡ 진행 중

| # | 내용 | 비고 |
|---|---|---|
| ✅ | Terraform — AWS VPC + ECS(Fargate) + RDS + ECR + ALB + CloudFront (서울 리전) | SCRUM-67 |
| ✅ | GitHub Actions CI/CD — ECR → ECS + S3+CloudFront | SCRUM-68 |
| ✅ | 손으로 작성한 OpenAPI 3.0 명세를 Swagger UI(`/docs`)가 서빙 | SCRUM-100 |
| 🔲 | AWS Secrets Manager 시크릿 관리 | P0 |
| 🔲 | Sentry 예외 추적 | P1 |
| 🔲 | Langfuse LLM 관찰성 연동 | P1 |

---

## API 엔드포인트 현황

| Method | Path | 상태 | 설명 |
|---|---|---|---|
| `GET` | `/health` | ✅ | 헬스체크 |
| `GET` | `/docs` | ✅ | Swagger UI (손으로 작성한 `openapi.yaml` 서빙) |
| `POST` | `/v1/auth/kakao` | ✅ | 카카오 로그인 → JWT 발급 |
| `POST` | `/v1/auth/refresh` | ✅ | access 토큰 갱신 (refresh 회전) |
| `POST` | `/v1/auth/logout` | ✅ | 로그아웃 (전체 토큰 폐기) |
| `GET` | `/v1/users/me` | ✅ | 내 정보 조회 |
| `PATCH` | `/v1/users/me` | ✅ | 내 정보·취향 수정 |
| `DELETE` | `/v1/users/me` | ✅ | 회원 탈퇴 (PIPA 익명화) |
| `GET` | `/v1/users/me/courses` | ✅ | 내가 생성한 코스 모아보기 (커서 페이지네이션) |
| `GET` | `/v1/stations` | ✅ | 역 목록 조회 (bounds 필터 + 노선) |
| `GET` | `/v1/stations/search` | ✅ | 역 이름 자동완성 |
| `GET` | `/v1/stations/{id}` | ✅ | 단일 역 조회 |
| `GET` | `/v1/courses` | ✅ | 코스 목록 (필터 + 커서 페이지네이션) |
| `GET` | `/v1/courses/{id}` | ✅ | 코스 상세 (OG 태그 포함) |
| `POST` | `/v1/courses/recommend` | ✅ | AI 코스 추천 (로그인 필수, 일 3회, `NEEDS_CLARIFICATION` 분기) |
| `GET` | `/v1/recommend/placeholder` | ✅ | 동적 입력창 placeholder (날씨·시간대·최근 질문) |
| `POST` | `/v1/courses/{id}/reviews` | ✅ | 리뷰 등록/수정 (upsert) |
| `GET` | `/v1/courses/{id}/reviews` | ✅ | 리뷰 목록 (커서 페이지네이션) |
| `DELETE` | `/v1/courses/{id}/reviews/me` | ✅ | 내 리뷰 삭제 |
| `POST` | `/v1/places/{id}/report` | ✅ | 장소 정보 사용자 제보(영업시간·가격·별점) |
| ~~`POST`~~ | ~~`/v1/courses/{id}/reviews/{rid}/report`~~ | ❌ 삭제됨 | 리뷰 신고 — 미사용 확인 후 제거(SCRUM-91) |

---

## CI/CD 설정

### GitHub Secrets 등록 목록

| Secret 이름 | 설명 |
|---|---|
| `AWS_ROLE_ARN` | OIDC 자격증명용 IAM Role ARN (e.g. `arn:aws:iam::123456789012:role/github-actions-role`) |
| `ECR_REPOSITORY` | ECR 리포지토리 이름 (e.g. `whatwedoin-backend`) |
| `ECS_CLUSTER` | ECS 클러스터 이름 (e.g. `whatwedoin-cluster`) |
| `ECS_SERVICE` | ECS 서비스 이름 (e.g. `whatwedoin-backend-service`) |
| `S3_BUCKET` | 프론트엔드 정적 파일 S3 버킷 이름 |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront 배포 ID |
| `NEXT_PUBLIC_API_URL` | 프론트엔드에서 사용할 백엔드 API URL |

### AWS OIDC IAM Role 설정

장기 자격증명 없이 GitHub Actions에서 AWS 리소스에 접근하려면 OIDC Provider와 IAM Role을 설정해야 합니다.

**1. IAM OIDC Provider 등록** (계정당 1회)

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**2. IAM Role Trust Policy** (`trust-policy.json`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:JinWook505/subway-date:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

**3. IAM Role 생성**

```bash
aws iam create-role \
  --role-name github-actions-whatwedoin \
  --assume-role-policy-document file://trust-policy.json

# 필요한 정책 연결
aws iam attach-role-policy \
  --role-name github-actions-whatwedoin \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name github-actions-whatwedoin \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

# S3 + CloudFront는 인라인 정책으로 최소 권한 부여
```

### 워크플로우 구성

| 파일 | 트리거 | 동작 |
|---|---|---|
| `.github/workflows/ci.yml` | PR → main | Backend pytest + Frontend Jest/tsc + 빌드 검증 |
| `.github/workflows/deploy-backend.yml` | push main (backend/**) | ECR 빌드·푸시 → ECS 롤링 업데이트 |
| `.github/workflows/deploy-frontend.yml` | push main (frontend/**) | Next.js 빌드 → S3 업로드 → CloudFront 무효화 |

---

## 주요 정책 요약

- **위치 입력**: 역 수동 선택 UI 없음. 질의어 자연어에서 지명·동네를 LLM이 추출해 최근접 지원 역으로 자동 매핑(D-20). 위치·필수 정보가 부족하면 추가 입력 Step(`NEEDS_CLARIFICATION`)으로 보완.
- **인증 게이트**: AI 코스 생성만 로그인 필수. 조회·리뷰·장소 제보는 비로그인 허용.
- **일일 한도**: 로그인 유저 하루 3회 무료 생성 (`ratelimit.user_daily=3`). 멱등 재요청·캐시 적중은 미차감.
- **베이지안 평균**: 랭킹은 단순 평균이 아닌 `(C·m + Σscore) / (C + n)` (m=50, C=5).
- **단일 역 정책**: 코스는 항상 정확히 1개 역 기준. 다중 역은 V2.
- **단계별 복수 대안**: 코스는 2~4개 단계(단일 카테고리 요청은 1단계도 허용)로 구성되고, 각 단계는 1~3개 대안을 제공해 사용자가 조합을 완성한다(D-26/D-29).
- **비식별**: 코스에 생성자 저장 안 함. 비로그인 리뷰 식별은 IP 해시만 저장.
- **LLM 전략**: 질의어 분류는 저비용 모델(`claude-haiku-4-5`), 코스 생성은 후보 풀 검증·재시도 포함. Provider 추상화로 Anthropic/Gemini 전환 가능.
- **카카오 API 미제공 항목** (`business_hours`, `rating`, `price_range`): 사용자 직접 제보(`/v1/places/{id}/report`)로 수집. 크롤링은 법무 확인 후 V2.
- **메뉴 특화 요청**: 후보 중 이름이 일치하는 장소를 우선 배치하고, 오프라인 캐시에 없으면 카카오 키워드 API를 실시간 호출해 보강(D-28).
- **리뷰 신고 기능은 제거됨**(D-27) — 미사용 확인 후 모델·라우터·테이블 전수 삭제. 재도입 시 V2에서 별도 설계 필요.
