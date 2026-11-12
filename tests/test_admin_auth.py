import threading
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.database.database import engine
from src.main import app
from src.models.admin import AdminUser, PasswordToken
from src.services.admin_bootstrap import issue_password_link, sync_admins
from tests.conftest import ADMIN_TEST_EMAIL, ADMIN_TEST_PASSWORD


def _token_from_link(link: str) -> str:
    return link.split("token=", 1)[1]


def _admins(db):
    return {a.email: a for a in db.scalars(select(AdminUser))}


# --- sync_admins -----------------------------------------------------------

def test_sync_creates_normalised_admins(db):
    assert sync_admins(db, [" Owner@X.com ", "owner@x.com", ""]) == ["owner@x.com"]
    assert list(_admins(db)) == ["owner@x.com"]


def test_sync_second_run_creates_nothing(db):
    sync_admins(db, ["owner@x.com"])
    assert sync_admins(db, ["owner@x.com"]) == []


def test_sync_deactivates_removed(db):
    sync_admins(db, ["a@x.com", "b@x.com"])
    sync_admins(db, ["a@x.com"])
    admins = _admins(db)
    assert admins["a@x.com"].is_active is True
    assert admins["b@x.com"].is_active is False


def test_sync_reactivates_relisted(db):
    sync_admins(db, ["a@x.com", "b@x.com"])
    sync_admins(db, ["a@x.com"])
    sync_admins(db, ["a@x.com", "b@x.com"])
    assert _admins(db)["b@x.com"].is_active is True


def test_empty_admin_emails_keeps_existing_admins_active(db):
    sync_admins(db, ["a@x.com"])
    assert sync_admins(db, []) == []
    assert _admins(db)["a@x.com"].is_active is True


def test_concurrent_sync_creates_one_row_one_email():
    email = "race@x.com"
    barrier = threading.Barrier(2)
    results = []

    def worker():
        with Session(engine) as session:
            barrier.wait()
            results.append(sync_admins(session, [email]))

    try:
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        with Session(engine) as session:
            rows = session.scalars(select(AdminUser).where(AdminUser.email == email)).all()
        assert len(rows) == 1
        assert sorted(results) == [[], [email]]
    finally:
        with engine.begin() as conn:
            conn.execute(delete(AdminUser).where(AdminUser.email == email))


# --- startup ---------------------------------------------------------------

def test_startup_sends_set_password_link_once(client, monkeypatch, sent_emails):
    monkeypatch.setattr(settings, "admin_emails", "new.owner@x.com")
    with TestClient(app):
        pass
    with TestClient(app):
        pass
    to_new = [e for e in sent_emails if e["to"] == "new.owner@x.com"]
    assert len(to_new) == 1
    assert "/admin/set-password?token=" in to_new[0]["html"]


def test_startup_survives_email_failure(client, monkeypatch):
    from src.services.email_service import email_service

    def boom(*args, **kwargs):
        raise RuntimeError("brevo down")

    monkeypatch.setattr(email_service, "send_email", boom)
    monkeypatch.setattr(settings, "admin_emails", "fails@x.com")
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200


# --- set password + login --------------------------------------------------

def _new_admin_link(db, email="owner@x.com", purpose="set"):
    sync_admins(db, [email])
    admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
    return admin, issue_password_link(db, admin, purpose)


def test_set_password_then_login(client, db):
    _, link = _new_admin_link(db)
    r = client.post("/api/admin/auth/set-password", json={"token": _token_from_link(link), "password": "a-long-password"})
    assert r.status_code == 204, r.text
    r = client.post("/api/admin/auth/login", json={"email": "owner@x.com", "password": "a-long-password"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["expires_in"] == 86400
    r = client.post(
        "/api/admin/auth/login",
        json={"email": "owner@x.com", "password": "a-long-password", "remember_me": True},
    )
    assert r.json()["expires_in"] == 2592000


def test_set_password_too_short_422(client, db):
    _, link = _new_admin_link(db)
    r = client.post("/api/admin/auth/set-password", json={"token": _token_from_link(link), "password": "short"})
    assert r.status_code == 422


def test_token_single_use(client, db):
    _, link = _new_admin_link(db)
    body = {"token": _token_from_link(link), "password": "a-long-password"}
    assert client.post("/api/admin/auth/set-password", json=body).status_code == 204
    assert client.post("/api/admin/auth/set-password", json=body).status_code == 400


def test_expired_link_rejected(client, db):
    admin, link = _new_admin_link(db)
    token = db.scalar(select(PasswordToken).where(PasswordToken.admin_id == admin.id))
    token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.flush()
    r = client.post("/api/admin/auth/set-password", json={"token": _token_from_link(link), "password": "a-long-password"})
    assert r.status_code == 400


def test_set_password_invalidates_other_links(client, db):
    admin, first = _new_admin_link(db)
    second = issue_password_link(db, admin, "reset")
    assert client.post("/api/admin/auth/set-password", json={"token": _token_from_link(second), "password": "a-long-password"}).status_code == 204
    assert client.post("/api/admin/auth/set-password", json={"token": _token_from_link(first), "password": "other-password"}).status_code == 400


def test_login_wrong_password_401(client, admin_user):
    r = client.post("/api/admin/auth/login", json={"email": ADMIN_TEST_EMAIL, "password": "nope"})
    assert r.status_code == 401


def test_login_unknown_email_401(client):
    r = client.post("/api/admin/auth/login", json={"email": "ghost@x.com", "password": "whatever"})
    assert r.status_code == 401


def test_login_email_case_insensitive(client, admin_user):
    r = client.post("/api/admin/auth/login", json={"email": "  ADMIN@Example.com ", "password": ADMIN_TEST_PASSWORD})
    assert r.status_code == 200


def test_login_rate_limited(client, admin_user):
    for _ in range(5):
        assert client.post("/api/admin/auth/login", json={"email": ADMIN_TEST_EMAIL, "password": "nope"}).status_code == 401
    r = client.post("/api/admin/auth/login", json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD})
    assert r.status_code == 429


def test_login_sets_last_login(client, db, admin_user):
    client.post("/api/admin/auth/login", json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD})
    db.refresh(admin_user)
    assert admin_user.last_login_at is not None


# --- forgot password -------------------------------------------------------

def test_forgot_password_unknown_email_still_202(client, sent_emails):
    r = client.post("/api/admin/auth/forgot-password", json={"email": "ghost@x.com"})
    assert r.status_code == 202
    assert sent_emails == []


def test_forgot_password_known_email_sends_reset(client, admin_user, sent_emails):
    r = client.post("/api/admin/auth/forgot-password", json={"email": "Admin@Example.com"})
    assert r.status_code == 202
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == ADMIN_TEST_EMAIL
    assert "/admin/set-password?token=" in sent_emails[0]["html"]


def test_inactive_admin_gets_no_reset_link(client, db, admin_user, sent_emails):
    admin_user.is_active = False
    db.flush()
    client.post("/api/admin/auth/forgot-password", json={"email": ADMIN_TEST_EMAIL})
    assert sent_emails == []


def test_inactive_admin_link_refused(client, db):
    admin, link = _new_admin_link(db)
    admin.is_active = False
    db.flush()
    r = client.post("/api/admin/auth/set-password", json={"token": _token_from_link(link), "password": "a-long-password"})
    assert r.status_code == 400


# --- require_admin ---------------------------------------------------------

def test_me_returns_admin(client, admin_headers):
    r = client.get("/api/admin/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_TEST_EMAIL


def test_missing_header_401_not_403(client):
    r = client.get("/api/admin/auth/me")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_garbage_token_401(client):
    assert client.get("/api/admin/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_deactivated_admin_token_rejected(client, db, admin_user, admin_headers):
    admin_user.is_active = False
    db.flush()
    assert client.get("/api/admin/auth/me", headers=admin_headers).status_code == 401
