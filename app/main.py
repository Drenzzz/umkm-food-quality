from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.detect import router as detect_router
from app.routers.health import router as health_router
from app.routers.history import router as history_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UMKM Food Quality API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(detect_router)
    app.include_router(history_router)
    app.include_router(admin_router)
    app.include_router(health_router)

    return app


app = create_app()
