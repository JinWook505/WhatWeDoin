# WhatWeDoin

"오늘 뭐하고 놀지?" AI가 지하철역 기반으로 놀거리 코스를 즉시 추천해주는 서비스.

## 로컬 개발 시작 순서

### 사전 준비

```bash
cp .env.example .env
# .env에서 필요한 값 설정 (ANTHROPIC_API_KEY 등)
```

### ① DB 기동

```bash
docker compose up -d
# db 컨테이너가 healthy 상태가 될 때까지 대기
docker compose ps
```

### ② Backend 기동

```bash
cd backend
cp .env.example .env
docker compose up
# http://localhost:8080/health 에서 200 확인
```

### ③ Frontend 기동

```bash
cd frontend
cp .env.example .env.local   # 또는 .env.local 직접 작성
docker compose up
# http://localhost:3000 에서 확인
```

## 스키마 초기화 / 재생성

`db/init.sql`을 수정한 뒤:

```bash
docker compose down -v
docker compose up -d
```
