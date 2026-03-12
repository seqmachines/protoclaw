from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from protocrawl.api.routes import (
    health,
    pipeline,
    protocols,
    reviews,
    slack,
    submissions,
)
from protocrawl.config import settings
from protocrawl.db.engine import engine
from protocrawl.db.tables import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Protocrawl",
        description="Sequencing protocol knowledge base API",
        version="0.1.0",
        lifespan=lifespan,
    )
    allow_origins = ["*"]
    if settings.cors_allow_origins.strip() and settings.cors_allow_origins.strip() != "*":
        allow_origins = [
            origin.strip()
            for origin in settings.cors_allow_origins.split(",")
            if origin.strip()
        ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(
        protocols.router, prefix="/protocols", tags=["protocols"]
    )
    application.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
    application.include_router(
        submissions.router, prefix="/submissions", tags=["submissions"]
    )
    application.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
    application.include_router(slack.router, prefix="/slack", tags=["slack"])
    return application


app = create_app()
