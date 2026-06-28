# WhatWeDoin — Claude 작업 가이드

## 프로젝트 개요

"오늘 뭐하고 놀지?" AI가 지하철역 기반으로 놀거리 코스를 즉시 추천해주는 서비스.  
PRD 전문: `prd.md`

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | Next.js 16 (TypeScript, App Router) |
| Backend | Python 3.12 + FastAPI |
| DB | PostgreSQL 16 + PostGIS (AWS RDS) |
| IaC | Terraform (AWS — ECS, RDS) |
| CI/CD | GitHub Actions (OIDC, ECR → ECS / S3+CloudFront) |

---

## Jira 티켓 기반 Git 브랜치 워크플로우

> **도구 원칙**
> - Jira 조회·상태 전환·설명 수정 → **Jira MCP** (`mcp__atlassian__*`)
> - Git/GitHub 작업 전반 → **`gh`**
> - 로컬 스테이징·커밋 → **`git add / git commit`** (gh 대체 불가)

---

### 1단계 — 티켓 확인 (Jira MCP)

```
mcp__atlassian__getJiraIssue(issueIdOrKey: "SCRUM-XX")
```

확인 항목:
- 티켓 제목 및 작업 설명
- 인수조건 (Given / When / Then 체크리스트)

---

### 2단계 — 브랜치 생성 + 티켓 진행 중 전환

**브랜치 명명 규칙**

```
feat/SCRUM-{번호}-{kebab-case-설명}   # 기능 개발
fix/SCRUM-{번호}-{kebab-case-설명}    # 버그 수정
chore/SCRUM-{번호}-{kebab-case-설명}  # 설정·문서
```

**실행** (두 작업 동시 진행)

```bash
# 로컬 브랜치 생성
gh repo sync                              # main 최신화
git checkout -b feat/SCRUM-{번호}-{설명}
```

```
# Jira MCP: "진행 중" 전환 (transition id: "21")
mcp__atlassian__transitionJiraIssue(issueIdOrKey: "SCRUM-XX", transition: {id: "21"})
```

---

### 3단계 — 구현 + 커밋

커밋 메시지 형식:

```
feat(SCRUM-{번호}): {변경 내용 한 줄 요약}
```

```bash
git add {파일}
git commit -m "feat(SCRUM-{번호}): {내용}"
```

---

### 4단계 — 인수조건 검증

티켓의 모든 체크리스트 항목을 실제로 확인한다.  
**미충족 항목이 하나라도 있으면 다음 단계로 넘어가지 않는다.**

```bash
cd frontend && npm test   # Frontend
cd backend  && pytest     # Backend
```

---

### 5단계 — PR 생성 + 머지 (gh)

```bash
# 원격 브랜치 push + PR 생성
gh pr create \
  --title "feat(SCRUM-{번호}): {티켓 제목}" \
  --body "Closes SCRUM-{번호}" \
  --base main

# 인수조건 전부 [x] 확인 후 머지 + 브랜치 자동 삭제
gh pr merge --merge --delete-branch
```

---

### 6단계 — 티켓 완료 처리 (Jira MCP)

```
# "완료" 전환 (transition id: "41")
mcp__atlassian__transitionJiraIssue(issueIdOrKey: "SCRUM-XX", transition: {id: "41"})

# 인수조건 체크박스 전부 [x]로 업데이트
mcp__atlassian__editJiraIssue(issueIdOrKey: "SCRUM-XX", fields: {description: "..."})
```

---

### 워크플로우 한눈에 보기

```
[Jira MCP] 티켓 확인
      ↓
[gh]       repo sync → 브랜치 생성
[Jira MCP] 티켓 → "진행 중"
      ↓
[git]      구현 + 커밋 (add/commit)
      ↓
[gh/npm/pytest] 테스트 Green 확인
[Jira MCP] 인수조건 체크박스 전부 [x] 확인
      ↓
[gh]       pr create → pr merge → 브랜치 삭제
      ↓
[Jira MCP] 티켓 → "완료" + 체크박스 업데이트
```

---

### 규칙

- `main` 직접 커밋 금지 — 반드시 `gh pr merge`로 머지
- 인수조건 미충족 시 PR 머지 금지
- `.env`, `.env.local`, `terraform.tfvars` 커밋 금지

---

## 디렉토리 구조

```
WhatWeDoin/
├── frontend/           # Next.js 16        (SCRUM-64)
├── backend/            # FastAPI            (SCRUM-65)
├── docker-compose.yml  # 루트: DB            (SCRUM-66)
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
