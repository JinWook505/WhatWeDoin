---
description: "Jira 티켓 시작: 이슈 조회 -> 브랜치 생성 + In Progress 전환 -> 구현 + 커밋. 사용법: /ticket-start SCRUM-XX [feat|fix|chore]"
allowed-tools: ["mcp__atlassian__getJiraIssue", "mcp__atlassian__transitionJiraIssue", "Bash", "Read", "Write", "Edit", "Glob", "Grep"]
---

$ARGUMENTS에서 다음을 파싱하세요:
- **TICKET_KEY**: `SCRUM-[0-9]+` 패턴 — 없으면 "Usage: /ticket-start SCRUM-XX [feat|fix|chore]" 출력 후 중단
- **BRANCH_TYPE**: `feat` | `fix` | `chore` — 없으면 기본값 `feat`

## Step 1 — 티켓 조회

`mcp__atlassian__getJiraIssue(issueIdOrKey: TICKET_KEY)` 호출.

다음을 확인합니다:
- 티켓 제목 및 작업 설명
- 인수조건 체크리스트 (`[ ]` / `[x]` 항목 전부)

티켓 상태가 이미 "In Progress" 또는 "Done"이면 경고를 출력하고 계속할지 확인을 구하세요.

## Step 2 — 브랜치 생성 + 진행 중 전환

두 작업을 동시에 진행합니다.

**브랜치 생성:**

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

**진행 중 전환:**

`mcp__atlassian__transitionJiraIssue(issueIdOrKey: TICKET_KEY, transition: {id: "21"})`

## Step 3 — 구현 + 커밋

티켓의 작업 설명과 인수조건을 모두 충족하도록 **실제 코드를 직접 구현**합니다.

구현 원칙:
- 티켓의 "작업 순서"가 있으면 그 순서대로 진행합니다
- TDD가 명시된 경우 Red → Green 순서를 지킵니다 (테스트 먼저 작성 후 구현)
- 인수조건의 모든 `[ ]` 항목이 충족되도록 구현합니다
- 기존 코드베이스의 패턴과 컨벤션을 따릅니다

구현이 완료되면 논리적 단위로 나눠 커밋합니다:

```bash
git add <파일>
git commit -m "{BRANCH_TYPE}(SCRUM-{NUMBER}): <변경 내용 한 줄 요약>"
```

## Step 4 — 결과 출력

```
브랜치 생성 : {브랜치명}
티켓 상태  : In Progress

구현 완료 항목:
  [x] <인수조건 항목 1>
  [x] <인수조건 항목 2>
  ...

커밋 목록:
  - {BRANCH_TYPE}(SCRUM-{NUMBER}): <커밋 메시지 1>
  - {BRANCH_TYPE}(SCRUM-{NUMBER}): <커밋 메시지 2>
  ...

완료 후: /ticket-done 실행으로 테스트 검증 + PR 생성 및 티켓 종료
```
