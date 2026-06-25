# WhatWeDoin — 프로젝트 가이드 (for Claude)

## 프로젝트 개요

선택한 지하철역 1개를 기준으로 AI가 데이트 플랜을 즉시 생성해주는 서비스.
PRD: `prd.md` 참조.

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 (TypeScript, App Router) |
| Backend | Python 3.12 + FastAPI |
| DB | PostgreSQL 16 + PostGIS |
| Cache | Redis 7 |
| IaC | Terraform (AWS ECS + RDS + ElastiCache) |
| CI/CD | GitHub Actions (OIDC, ECR, S3+CloudFront) |

---

## Git 워크플로우

### 브랜치 전략

**Jira 티켓 1개 = 브랜치 1개.** 작업을 시작할 때 반드시 티켓 번호를 포함한 브랜치를 생성한다.

```
브랜치 명명 규칙: feat/SCRUM-{번호}-{간단한-설명}
예시:
  feat/SCRUM-65-fastapi-setup
  feat/SCRUM-66-docker-compose
  fix/SCRUM-99-health-check-bug
```

### 작업 순서

1. **브랜치 생성** — 티켓 작업 시작 시 `main`에서 브랜치를 딴다.
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/SCRUM-{번호}-{설명}
   ```

2. **Jira 전환** — 브랜치 생성 후 해당 티켓을 **진행 중**으로 전환한다.

3. **구현 + 커밋** — 작업 단위로 커밋한다. 커밋 메시지 앞에 티켓 번호를 붙인다.
   ```
   [SCRUM-65] FastAPI 프로젝트 초기화 및 /health 엔드포인트 구현
   ```

4. **인수조건 검증** — 티켓의 모든 인수조건(Given/When/Then 체크리스트)이 실제로 충족되었는지 확인한다. 체크리스트가 전부 [x]가 되어야 머지할 수 있다.

5. **머지** — 인수조건이 **찐찐으로 100% 완료**된 경우에만 `main`으로 머지한다.
   ```bash
   git checkout main
   git merge --no-ff feat/SCRUM-{번호}-{설명} -m "Merge feat/SCRUM-{번호}: {티켓 제목}"
   git push origin main
   ```

6. **Jira 완료** — 머지 후 해당 티켓을 **완료**로 전환하고 인수조건 체크박스를 모두 [x]로 업데이트한다.

### 규칙

- `main` 브랜치에 직접 커밋하지 않는다.
- 인수조건이 하나라도 미충족이면 머지하지 않는다.
- 머지 전 `npm test` (frontend) 또는 `pytest` (backend)가 반드시 Green이어야 한다.
- 시크릿/환경변수(`.env`, `.env.local`, `terraform.tfvars`)는 절대 커밋하지 않는다.

---

## 디렉토리 구조

```
WhatWeDoin/
├── frontend/          # Next.js 16 (SCRUM-64)
├── backend/           # FastAPI (SCRUM-65)
├── terraform/         # AWS IaC (SCRUM-67)
├── .github/
│   └── workflows/     # CI/CD (SCRUM-68)
├── docker-compose.yml # 루트: db + cache (SCRUM-66)
├── .gitignore
├── CLAUDE.md          # 이 파일
└── prd.md
```

## 로컬 개발 환경 시작 순서

```bash
# 1. 루트: DB + Cache 기동
docker compose up -d

# 2. 백엔드 기동
cd backend && docker compose up

# 3. 프론트엔드 기동 (또는 로컬 직접 실행)
cd frontend && npm run dev
```
