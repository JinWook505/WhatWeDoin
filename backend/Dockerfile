FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

EXPOSE 8080

# uv sync: named volume(.venv)이 비어있는 첫 실행 시 패키지 설치
# --reload: 코드 변경 시 uvicorn 자동 재시작 (hot-reload)
CMD ["sh", "-c", "uv sync --frozen && uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"]
