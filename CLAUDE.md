# WhatWeDoin — Claude 작업 가이드

## 프로젝트 개요

선택한 지하철역 1개를 기준으로 AI가 데이트 플랜을 즉시 생성해주는 서비스.  
PRD 전문: `prd.md`

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 (TypeScript, App Router) |
| Backend | Python 3.12 + FastAPI |
| DB | PostgreSQL 16 + PostGIS |
| Cache | Redis 7 |
| IaC | Terraform (AWS — ECS, RDS, ElastiCache) |
| CI/CD | GitHub Actions (OIDC, ECR → ECS / S3+CloudFront) |

---

## Jira 티켓 기반 Git 브랜치 워크플로우

> **도구 원칙**
> - Jira 조회·상태 전환·설명 수정 → **Jira MCP** (`mcp__atlassian__*`)
> - Git 브랜치·커밋·PR·머지 → **gh CLI** (`gh`, `git`)

---

### 1단계 — 티켓 확인 (Jira MCP)

작업 전 반드시 티켓 내용을 읽는다.

```
mcp__atlassian__getJiraIssue(issueIdOrKey: "SCRUM-XX")
```

확인 항목:
- 티켓 제목 및 작업 설명
- 인수조건(Given / When / Then 체크리스트)

---

### 2단계 — 브랜치 생성 + 티켓 진행 중 전환

**브랜치 명명 규칙**

```
feat/SCRUM-{번호}-{kebab-case-설명}   # 기능 개발
fix/SCRUM-{번호}-{kebab-case-설명}    # 버그 수정
chore/SCRUM-{번호}-{kebab-case-설명}  # 설정·문서
```

**실행 순서** (두 작업 동시 진행)

```bash
# git: main 최신화 후 브랜치 생성
git checkout main && git pull origin main
git checkout -b feat/SCRUM-{번호}-{설명}
```

```
# Jira MCP: 티켓 상태를 "진행 중"으로 전환
mcp__atlassian__transitionJiraIssue(issueIdOrKey: "SCRUM-XX", transition.id: "21")
```

---

### 3단계 — 구현 + 커밋

커밋 메시지 형식:

```
feat(SCRUM-{번호}): {변경 내용 한 줄 요약}
```

예시:
```
feat(SCRUM-65): FastAPI /health 엔드포인트 구현
fix(SCRUM-99): Redis 연결 타임아웃 처리
```

---

### 4단계 — 인수조건 검증

티켓의 모든 체크리스트 항목을 실제로 확인한다.  
**미충족 항목이 하나라도 있으면 다음 단계로 넘어가지 않는다.**

테스트 통과 확인:
```bash
# Frontend
cd frontend && npm test

# Backend
cd backend && pytest
```

---

### 5단계 — PR 생성 + 머지 (gh CLI)

```bash
# PR 생성
gh pr create \
  --title "feat(SCRUM-{번호}): {티켓 제목}" \
  --body "Closes SCRUM-{번호}" \
  --base main \
  --head feat/SCRUM-{번호}-{설명}

# 인수조건 전부 [x] 확인 후 머지
gh pr merge {PR번호} --merge --delete-branch
```

---

### 6단계 — 티켓 완료 처리 (Jira MCP)

```
# 상태를 "완료"로 전환
mcp__atlassian__transitionJiraIssue(issueIdOrKey: "SCRUM-XX", transition.id: "41")

# 인수조건 체크박스 [x] 업데이트
mcp__atlassian__editJiraIssue(issueIdOrKey: "SCRUM-XX", fields.description: "...")
```

---

### 워크플로우 요약

```
[Jira MCP] 티켓 확인
      ↓
[git] main pull → 브랜치 생성
[Jira MCP] 티켓 → "진행 중"
      ↓
[git] 구현 + 커밋
      ↓
[테스트] npm test / pytest → Green 필수
[Jira MCP] 인수조건 체크박스 전부 [x] 확인
      ↓
[gh] PR 생성 → 머지 → 브랜치 삭제
      ↓
[Jira MCP] 티켓 → "완료" + 체크박스 업데이트
```

---

### 규칙

- `main` 직접 커밋 금지 — 반드시 PR을 통해 머지
- 인수조건 미충족 시 PR 머지 금지
- `.env`, `.env.local`, `terraform.tfvars` 커밋 금지

---

## 디렉토리 구조

```
WhatWeDoin/
├── frontend/           # Next.js 16        (SCRUM-64)
├── backend/            # FastAPI            (SCRUM-65)
├── docker-compose.yml  # 루트: DB + Cache   (SCRUM-66)
├── terraform/          # AWS IaC            (SCRUM-67)
├── .github/workflows/  # CI/CD             (SCRUM-68)
├── .gitignore
├── CLAUDE.md
└── prd.md
```

## 로컬 개발 시작 순서

```bash
# 1. DB + Cache
docker compose up -d

# 2. Backend
cd backend && docker compose up

# 3. Frontend
cd frontend && npm run dev
```
