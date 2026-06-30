from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import health
from app.routers import places

app = FastAPI(title="WhatWeDoin API")

app.include_router(health.router)
app.include_router(places.router)

Instrumentator().instrument(app).expose(app)
