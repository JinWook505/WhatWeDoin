from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import auth, courses, health, places, recommend, reviews, stations, users

app = FastAPI(title="WhatWeDoin API")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(stations.router)
app.include_router(courses.router)
app.include_router(reviews.router)
app.include_router(reviews.report_router)
app.include_router(places.router)
app.include_router(recommend.router)
app.include_router(recommend.placeholder_router)
app.include_router(users.router)

Instrumentator().instrument(app).expose(app)
