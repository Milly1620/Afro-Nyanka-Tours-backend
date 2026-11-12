import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:test@localhost:5439/postgres"
)
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-chars"
os.environ.setdefault("BREVO_API_KEY", "test-brevo-key")
os.environ.setdefault("ADMIN_EMAIL", "ops@example.com")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.database import SessionLocal, engine, get_db
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
def connection():
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
    finally:
        trans.rollback()
        conn.close()


@pytest.fixture
def session_factory(connection):
    """Sessions bound to the per-test connection; all writes roll back."""
    return lambda: Session(bind=connection, join_transaction_mode="create_savepoint")


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from src.services.rate_limit import email_rate_limiter, login_rate_limiter

    for limiter in (login_rate_limiter, email_rate_limiter):
        limiter.reset_all()
    yield
    for limiter in (login_rate_limiter, email_rate_limiter):
        limiter.reset_all()


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []

    def fake_send(to_email, subject, html_content, **kwargs):
        sent.append({"to": to_email, "subject": subject, "html": html_content, **kwargs})
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    return sent


@pytest.fixture
def client(db, session_factory, sent_emails):
    app.dependency_overrides[get_db] = lambda: db
    app.state.session_factory = session_factory
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    app.state.session_factory = SessionLocal


ADMIN_TEST_EMAIL = "admin@example.com"
ADMIN_TEST_PASSWORD = "correct-horse-battery"


@pytest.fixture
def admin_user(db):
    from src.core.security import hash_password
    from src.models.admin import AdminUser

    admin = AdminUser(email=ADMIN_TEST_EMAIL, password_hash=hash_password(ADMIN_TEST_PASSWORD))
    db.add(admin)
    db.flush()
    return admin


@pytest.fixture
def admin_headers(client, admin_user):
    response = client.post(
        "/api/admin/auth/login",
        json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
