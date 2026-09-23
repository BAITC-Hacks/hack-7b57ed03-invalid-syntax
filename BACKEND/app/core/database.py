from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import meeting  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Small additive MVP migration. Existing user data is never dropped."""
    additions = {
        "participants": {"role": "VARCHAR(300)"},
        "transcript_segments": {
            "speaker_role": "VARCHAR(300)",
            "confidence": "FLOAT NOT NULL DEFAULT 0",
        },
        "summaries": {
            "summary_text": "TEXT NOT NULL DEFAULT ''",
            "risks_json": "TEXT NOT NULL DEFAULT '[]'",
            "metrics_json": "TEXT NOT NULL DEFAULT '[]'",
        },
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'))
