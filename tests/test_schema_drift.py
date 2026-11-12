from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from src.database.database import Base, engine
from src.models import admin, analytics, models  # noqa: F401


def test_migrations_match_models():
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    diff = [d for d in diff if not (isinstance(d, tuple) and d[0] == "remove_table" and d[1].name == "alembic_version")]
    assert diff == []
