# WhatWeDoin

"오늘 뭐하고 놀지?" AI가 지하철역 기반으로 놀거리 코스를 즉시 추천해주는 서비스.

> Z세대 타겟. 역 1개 + 한 문장 질의어로 동선이 잡힌 플랜을 즉시 생성. 비로그인 열람·리뷰 가능, AI 생성만 로그인 필수.

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js (App Router, TypeScript) |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.x (async) |
| DB | PostgreSQL 16 + PostGIS (AWS RDS) |
| LLM | Claude API (Anthropic) — Provider 추상화로 OpenAI 전환 대비 |
| 지도 | 카카오맵 JS SDK |
| 인증 | 카카오 OAuth 2.0 + 자체 JWT (access 30분, refresh 14일 회전) |
| IaC | Terraform (AWS ECS + RDS + ALB) |
| CI/CD | GitHub Actions (ECR → ECS / S3+CloudFront) |

---

## 로컬 개발

### 사전 준비

```bash
cp .env.example .env
# ANTHROPIC_API_KEY, KAKAO_REST_API_KEY 등 필수 값 입력
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
python scripts/seed_stations.py   # 역 + 노선 시딩
python scripts/etl_places.py      # 카카오 로컬 API 장소 수집
```

---

## 디렉토리 구조

```
WhatWeDoin/
├── frontend/               # Next.js 16 (App Router)
│   └── src/
│       ├── app/            # 페이지 (홈 · 결과 · /courses/[id])
│       ├── components/     # CourseTimeline · PlaceCard · ReportBottomSheet
│       └── lib/            # API 클라이언트
├── backend/                # FastAPI
│   ├── app/
│   │   ├── core/           # config · DB 세션
│   │   ├── models/         # SQLAlchemy ORM 모델 (전체 스키마)
│   │   ├── routers/        # health · stations · recommend · places
│   │   └── services/
│   │       ├── llm/        # LLM Provider 추상화 (Anthropic / Gemini)
│   │       ├── classifier.py      # 질의어 → theme_tags/budget/companion
│   │       ├── course_generator.py  # LLM 코스 생성 + 환각 검증
│   │       └── place_search.py    # PostGIS 반경 검색
│   ├── alembic/            # DB 마이그레이션 (4개)
│   ├── scripts/            # seed_stations · etl_places
│   └── tests/              # pytest 테스트 8종
├── db/init.sql             # 초기 스키마
├── docker-compose.yml      # 루트 (PostgreSQL + PostGIS)
├── terraform/              # AWS IaC (미구현)
└── .github/workflows/      # CI/CD (미구현)
```

---

## 구현 순서 및 진척도

> **전체 진척도: 약 40%** (Phase 1~3 완료, Phase 4~7 진행 예정)

### Phase 1 — 기반 구축 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | PostgreSQL + PostGIS DB 스키마 + Alembic 마이그레이션 (4개) | SCRUM-66 |
| ✅ | FastAPI 기본 구조 (`health`, `config`, async DB 세션) | SCRUM-65 |
| ✅ | 역 데이터 시딩 (`stations` + `station_lines` upsert) | SCRUM-73 |
| ✅ | 장소 ETL (카카오 로컬 REST API → `places` 적재) | SCRUM-72 |
| ✅ | `places.theme_tags` 컬럼 추가 + 카카오 카테고리 → enum 매핑 | SCRUM-72 |
| ✅ | LLM Provider 추상화 인터페이스 (Anthropic / Gemini 구현체) | SCRUM-71 |
| ✅ | 장소 정보 사용자 제보 API (`POST /v1/places/{id}/report`) | SCRUM-74 |

### Phase 2 — AI 추천 엔진 ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | LLM 질의어 분류기 (`theme_tags` · `budget_tier` · `companion_type` · `head_count` 추출) | SCRUM-37 |
| ✅ | PostGIS `ST_DWithin` 후보 장소 검색 (5km → 7km 확장) | SCRUM-38 |
| ✅ | LLM 코스 생성 + 환각 검증 (후보 풀 외 place_id 제거·재시도) | SCRUM-38 |
| ✅ | 추천 오케스트레이터 (`POST /v1/courses/recommend`, 캐시·멱등·한도 체크) | SCRUM-36 |

### Phase 3 — 프론트엔드 핵심 UI ✅ 완료

| # | 내용 | SCRUM |
|---|---|---|
| ✅ | 홈 화면 — 단일 텍스트 질의어 입력 (역명 자동 추출 포함) | SCRUM-45 |
| ✅ | 코스 결과 타임라인 UI + 장소 카드 | SCRUM-45 |
| ✅ | 장소 정보 제보 바텀시트 (`ReportBottomSheet`) | SCRUM-74 |
| ✅ | Z세대 다크 네온 디자인 리뉴얼 | — |
| ✅ | 동네·상권명 → 근처 역 자동 매핑 (LLM 보조) | — |

### Phase 4 — 인증 & 사용자 관리 🔲 미구현

| # | 내용 | 비고 |
|---|---|---|
| 🔲 | 카카오 OAuth → 자체 JWT 발급 (`POST /v1/auth/kakao`) | P0 |
| 🔲 | 토큰 갱신·로그아웃 (`/auth/refresh`, `/auth/logout`) | P0 |
| 🔲 | 온보딩 (약관 동의 + 선택 개인화 정보 입력) | P0 |
| 🔲 | 마이페이지 (`GET/PATCH/DELETE /v1/users/me`) | P1 |
| 🔲 | 프론트: 카카오 로그인 버튼 + 로그인 팝업 | P0 |
| 🔲 | 비로그인 추천 시도 → 로그인 팝업 유도 | P0 |

### Phase 5 — 코스 탐색 & 리뷰 🔲 미구현

| # | 내용 | 비고 |
|---|---|---|
| 🔲 | 코스 목록 API (`GET /v1/courses`) — 역·테마·인원·예산 필터 + 커서 페이지네이션 | P0 |
| 🔲 | 코스 상세 API (`GET /v1/courses/{id}`) — OG 태그 포함 | P0 |
| 🔲 | 코스 리뷰 API (`POST/GET/DELETE /v1/courses/{id}/reviews`) — 베이지안 평균 갱신 | P0 |
| 🔲 | 리뷰 신고 API (`POST /v1/courses/{id}/reviews/{id}/report`) | P1 |
| 🔲 | 프론트: 메인 코스 탐색 페이지 (필터 + 목록) | P0 |
| 🔲 | 프론트: 코스 상세 SSR 페이지 (`/courses/[id]`, OG 태그) | P0 |
| 🔲 | 프론트: 리뷰 작성 UI (100점·5단위 슬라이더 + 댓글 + 링크) | P0 |
| 🔲 | 비로그인 IP 리뷰 → 로그인 후 user_id 승격 병합 | P1 |

### Phase 6 — 지도 & 고도화 🔲 미구현

| # | 내용 | 비고 |
|---|---|---|
| 🔲 | 카카오맵 JS SDK 역 마커 선택 UI (프론트) | P0 |
| 🔲 | 역 이름 자동완성 검색 (`GET /v1/stations/search`) 프론트 연동 | P1 |
| 🔲 | 동적 Placeholder API (`GET /v1/recommend/placeholder`) — 날씨·시간대·최근 질문 | P1 |
| 🔲 | OpenWeatherMap 날씨 캐시 (30분 DB 캐시) | P1 |
| 🔲 | 추천 결과에 유사 테마 고득점 코스 3개 동반 노출 (`similar_top_courses`) | P0 |
| 🔲 | 신선도 배치 (월 1회, `last_synced_at` 30일 초과 재동기화) | P1 |
| 🔲 | 사후 방문 설문 (`POST /v1/courses/{id}/visit-survey`) | P2 |
| 🔲 | 레이트 리밋 실제 적용 (일일 생성 3회 · 비로그인 리뷰 IP 상한) | P0 |

### Phase 7 — 인프라 & 배포 🔲 미구현

| # | 내용 | 비고 |
|---|---|---|
| 🔲 | Terraform — AWS ECS + RDS + ALB (서울 리전) | SCRUM-67 |
| ✅ | GitHub Actions CI/CD — ECR → ECS (백엔드) + S3+CloudFront (프론트) | SCRUM-68 |
| 🔲 | Langfuse LLM 관찰성 연동 (프롬프트·토큰·비용 트레이스) | P1 |
| 🔲 | Sentry 예외 추적 | P1 |
| 🔲 | AWS Secrets Manager 시크릿 관리 | P0 |

---

## API 엔드포인트 현황

| Method | Path | 상태 | 설명 |
|---|---|---|---|
| `GET` | `/health` | ✅ | 헬스체크 |
| `GET` | `/v1/stations` | ✅ | 지도 뷰포트 내 역 마커 조회 |
| `GET` | `/v1/stations/search` | ✅ | 역 이름 자동완성 |
| `POST` | `/v1/courses/recommend` | ✅ | AI 코스 추천 (로그인 필수) |
| `POST` | `/v1/places/{id}/report` | ✅ | 장소 정보 사용자 제보 |
| `GET` | `/v1/courses` | 🔲 | 메인 코스 목록 + 필터 |
| `GET` | `/v1/courses/{id}` | 🔲 | 코스 상세 (SSR 데이터 소스) |
| `POST` | `/v1/courses/{id}/reviews` | 🔲 | 리뷰 등록/수정 |
| `GET` | `/v1/courses/{id}/reviews` | 🔲 | 리뷰 목록 |
| `DELETE` | `/v1/courses/{id}/reviews/me` | 🔲 | 내 리뷰 삭제 |
| `POST` | `/v1/courses/{id}/reviews/{rid}/report` | 🔲 | 리뷰 신고 |
| `GET` | `/v1/recommend/placeholder` | 🔲 | 동적 입력창 placeholder |
| `POST` | `/v1/courses/{id}/visit-survey` | 🔲 | 사후 방문 설문 |
| `POST` | `/v1/auth/kakao` | 🔲 | 카카오 로그인 → JWT 발급 |
| `POST` | `/v1/auth/refresh` | 🔲 | access 토큰 갱신 |
| `POST` | `/v1/auth/logout` | 🔲 | 로그아웃 |
| `GET` | `/v1/users/me` | 🔲 | 내 정보 조회 |
| `PATCH` | `/v1/users/me` | 🔲 | 내 정보 수정 |
| `DELETE` | `/v1/users/me` | 🔲 | 회원 탈퇴 |

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
| `.github/workflows/ci.yml` | PR → main | Backend pytest + Frontend Jest + 빌드 검증 |
| `.github/workflows/deploy-backend.yml` | push main (backend/**) | ECR 빌드·푸시 → ECS 롤링 업데이트 |
| `.github/workflows/deploy-frontend.yml` | push main (frontend/**) | Next.js 빌드 → S3 업로드 → CloudFront 무효화 |

---

## 주요 정책 요약

- **인증 게이트**: AI 코스 생성만 로그인 필수. 조회·리뷰는 비로그인 허용.
- **일일 한도**: 로그인 유저 하루 3회 무료 생성 (`ratelimit.user_daily=3`). 멱등 재요청·캐시 적중은 미차감.
- **베이지안 평균**: 랭킹은 단순 평균이 아닌 `(C·m + Σscore) / (C + n)` (m=50, C=5).
- **단일 역 정책**: `station_ids` 길이 1 고정. 다중 역은 V2.
- **비식별**: 코스에 생성자 저장 안 함. 비로그인 리뷰 식별은 IP 해시만 저장.
- **LLM 전략**: 질의어 분류는 저비용 모델(`claude-haiku-4-5-20251001`), 코스 생성은 고급 모델(`claude-sonnet-4-6`). Provider 추상화로 OpenAI 전환 가능.
- **카카오 API 미제공 항목** (`business_hours`, `rating`, `price_range`): 사용자 직접 제보(`/v1/places/{id}/report`)로 수집. 크롤링은 법무 확인 후 V2.
