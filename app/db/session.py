from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine_kwargs: dict = {"future": True}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif database_url.startswith("postgresql"):
    # Conservative pool sizing for a 4GB/2-vCPU VPS — avoid connection storms
    # when the gunicorn workers and admin scripts hit the DB simultaneously.
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 0
    engine_kwargs["pool_timeout"] = 30
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
