import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:test@localhost:5439/postgres"
)
os.environ["SECRET_KEY"] = "test-secret"
os.environ.setdefault("BREVO_API_KEY", "test-brevo-key")
os.environ.setdefault("ADMIN_EMAIL", "ops@example.com")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.database import engine, get_db
from src.main import app
from src.services.email_service import email_service

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def alembic_config(connection=None) -> Config:
    cfg = Config(os.path.join(ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    if connection is not None:
        cfg.attributes["connection"] = connection
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    with engine.begin() as conn:
        command.upgrade(alembic_config(conn), "head")
    yield


@pytest.fixture
def db():
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []

    def fake_send(to_email, subject, html_content, **kwargs):
        sent.append({"to": to_email, "subject": subject, "html": html_content, **kwargs})
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    return sent


@pytest.fixture
def client(db, sent_emails):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
