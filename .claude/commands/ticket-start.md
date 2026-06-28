---
description: "Jira 티켓 시작: 이슈 조회 → 브랜치 생성 → In Progress 전환. 사용법: /ticket-start SCRUM-XX [feat|fix|chore]"
allowed-tools: ["mcp__atlassian__getJiraIssue", "mcp__atlassian__transitionJiraIssue", "Bash"]
---

$ARGUMENTS에서 다음을 파싱하세요:
- **TICKET_KEY**: `SCRUM-[0-9]+` 패턴 — 없으면 "Usage: /ticket-start SCRUM-XX [feat|fix|chore]" 출력 후 중단
- **BRANCH_TYPE**: `feat` | `fix` | `chore` — 없으면 기본값 `feat`

## Step 1 — 티켓 조회

`mcp__atlassian__getJiraIssue(issueIdOrKey: TICKET_KEY)` 호출.

다음을 출력:
- 티켓 제목
- 설명
- 인수조건 체크리스트 (`[ ]` / `[x]` 항목 전부)

티켓 상태가 이미 "In Progress" 또는 "Done"이면 경고를 출력하고 계속할지 확인을 구하세요.

## Step 2 — main 동기화 + 브랜치 생성

```bash
gh repo sync
```

티켓 제목으로 슬러그 생성 규칙:
- 소문자로 변환
- 공백·특수문자 → 하이픈
- 연속 하이픈 → 단일 하이픈
- 최대 40자, 끝 하이픈 제거

브랜치명: `{BRANCH_TYPE}/SCRUM-{NUMBER}-{slug}`

```bash
git checkout -b {BRANCH_TYPE}/SCRUM-{NUMBER}-{slug}
```

## Step 3 — In Progress 전환

`mcp__atlassian__transitionJiraIssue(issueIdOrKey: TICKET_KEY, transition: {id: "21"})`

## Step 4 — 결과 출력

```
브랜치 생성 : {브랜치명}
티켓 상태  : In Progress

인수조건 — /ticket-done 실행 전 모두 충족 필요:
  [ ] <항목 1>
  [ ] <항목 2>
  ...

커밋 형식: {BRANCH_TYPE}(SCRUM-{NUMBER}): <내용>
완료 후: /ticket-done 실행으로 PR 생성 및 티켓 종료
```
