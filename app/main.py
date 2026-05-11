from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.base import Base
from app.db.session import engine
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="UMKM Food Quality API", lifespan=lifespan)
    app.include_router(auth_router)

    return app


app = create_app()
