"""SQLAlchemy engine + base. SQLite now, Postgres-swappable via the URL."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(db_url: str | None = None, *, echo: bool = False):
    from spec_manager.config import database_url

    url = db_url or database_url()
    in_memory = url.startswith("sqlite") and (":memory:" in url or url in ("sqlite://", "sqlite:///"))
    if in_memory:
        # One shared connection so an in-memory DB is visible across threads/requests.
        from sqlalchemy.pool import StaticPool

        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
            echo=echo,
        )
    if db_url is None and url.startswith("sqlite"):
        # Ensure the default data directory exists for a first run.
        from spec_manager.config import default_db_path

        default_db_path().parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True, echo=echo)


def init_db(engine) -> None:
    """Create all tables. Imports models so they register on Base.metadata."""
    from spec_manager import models  # noqa: F401

    Base.metadata.create_all(engine)
