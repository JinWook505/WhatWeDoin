---
description: "Jira 티켓 완료: 테스트 → 인수조건 검증 → PR 생성·머지 → 티켓 종료. 사용법: /ticket-done [SCRUM-XX]"
allowed-tools: ["mcp__atlassian__getJiraIssue", "mcp__atlassian__transitionJiraIssue", "mcp__atlassian__editJiraIssue", "Bash"]
---

$ARGUMENTS가 `SCRUM-[0-9]+` 패턴이면 TICKET_KEY로 사용. 아니면 현재 브랜치에서 추출:

```bash
git branch --show-current
```

예시: `feat/SCRUM-65-backend-setup` → TICKET_KEY=`SCRUM-65`, BRANCH_TYPE=`feat`

SCRUM 키를 찾을 수 없으면 STOP: "Cannot detect ticket key. Use: /ticket-done SCRUM-XX"

## Step 1 — 티켓 조회

`mcp__atlassian__getJiraIssue(issueIdOrKey: TICKET_KEY)` 호출.
- `ISSUE_SUMMARY`: PR 제목 suffix로 저장
- `ACCEPTANCE_CRITERIA`: 체크리스트 전체 저장

## Step 2 — 테스트 실행

**Frontend** (frontend/ 항상 실행):
```bash
cd frontend && npm test -- --passWithNoTests 2>&1
```

**Backend** (backend/ 디렉토리가 존재할 때만):
```bash
cd backend && pytest 2>&1
```

**HARD STOP**: 하나라도 비정상 종료(non-zero exit)이면 중단.
```
BLOCKED: 테스트 실패. 수정 후 /ticket-done 재실행.
```

## Step 3 — 인수조건 검증

```bash
git diff main...HEAD --stat
```

diff 결과와 테스트 결과를 바탕으로 각 인수조건 항목의 충족 여부를 판단.

**HARD STOP**: 미충족 항목이 하나라도 있으면 중단.
```
BLOCKED: 미충족 인수조건:
  [ ] <항목>
구현 완료 및 커밋 후 /ticket-done 재실행.
```

## Step 4 — PR 생성

```bash
gh pr create \
  --title "{BRANCH_TYPE}(SCRUM-{NUMBER}): {ISSUE_SUMMARY}" \
  --body "Closes SCRUM-{NUMBER}" \
  --base main
```

실패 시 에러 출력 후 STOP (머지·티켓 종료 금지).

## Step 5 — PR 머지

```bash
gh pr merge --merge --delete-branch
```

실패 시 에러 출력 후 STOP (티켓 종료 금지).

## Step 6 — 티켓 완료 전환

`mcp__atlassian__transitionJiraIssue(issueIdOrKey: TICKET_KEY, transition: {id: "41"})`

## Step 7 — 인수조건 체크박스 업데이트

`mcp__atlassian__getJiraIssue`로 현재 설명을 재조회한 뒤,
`mcp__atlassian__editJiraIssue`로 설명 내 `[ ]` → `[x]` 전체 교체.
(설명의 다른 내용은 그대로 유지)

## Step 8 — 완료 출력

```
완료.
  티켓 : SCRUM-{NUMBER} → Done
  PR   : main에 머지 (브랜치 삭제됨)
  인수조건: 전부 [x] 처리
```
