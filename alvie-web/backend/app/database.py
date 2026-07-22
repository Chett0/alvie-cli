import os
from typing import Annotated, Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Defaults to a file next to the app so `uvicorn app.main:app` works with no
# setup; the docker-compose service overrides this to point at a mounted
# volume so the database survives container restarts.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./alvie.db")

connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_db)]
