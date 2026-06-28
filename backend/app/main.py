from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import health

app = FastAPI(title="WhatWeDoin API")

app.include_router(health.router)

Instrumentator().instrument(app).expose(app)
