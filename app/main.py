import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging_config import RequestLoggingMiddleware, setup_logging
from app.db.base import Base
from app.db.session import engine
from app.ml.predictor import get_predictor
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.detect import router as detect_router
from app.routers.health import router as health_router
from app.routers.history import router as history_router


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)

    # create_all is only used for test/dev convenience. Production deployments
    # must run `alembic upgrade head` before starting the server so that schema
    # changes are applied in a controlled, reversible way.
    if settings.app_env in {"development", "test"}:
        Base.metadata.create_all(bind=engine)

    if settings.warmup_predictor_on_startup and settings.app_env != "test":
        try:
            get_predictor()
        except Exception:
            # Warmup is best-effort: backend should still serve auth/health
            # endpoints even if the model artefacts are missing in dev.
            logger.exception("Predictor warmup failed during startup")

    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UMKM Food Quality API", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
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
