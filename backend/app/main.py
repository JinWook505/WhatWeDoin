from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import auth, health, places, recommend, stations

app = FastAPI(title="WhatWeDoin API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(stations.router)
app.include_router(places.router)
app.include_router(recommend.router)

Instrumentator().instrument(app).expose(app)
