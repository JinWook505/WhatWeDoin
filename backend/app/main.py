from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.routers import auth, courses, health, places, recommend, reviews, stations, users
from app.services.llm.base import LLMUnavailableError

app = FastAPI(title="WhatWeDoin API")

# Serve the hand-authored OpenAPI spec (backend/openapi.yaml) at /docs instead of
# FastAPI's auto-generated schema — the auto-generated one lacks the descriptions,
# examples and NEEDS_CLARIFICATION branching documented by hand in that file.
_OPENAPI_SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


def _custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    with open(_OPENAPI_SPEC_PATH, encoding="utf-8") as f:
        app.openapi_schema = yaml.safe_load(f)
    return app.openapi_schema


app.openapi = _custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(LLMUnavailableError)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "LLM_UNAVAILABLE",
                "message": "AI 서비스에 일시적인 문제가 있어요. 잠시 후 다시 시도해 주세요.",
                "retry_after": 30,
            },
        },
    )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(stations.router)
app.include_router(courses.router)
app.include_router(reviews.router)
app.include_router(places.router)
app.include_router(recommend.router)
app.include_router(recommend.placeholder_router)
app.include_router(users.router)

Instrumentator().instrument(app).expose(app)
