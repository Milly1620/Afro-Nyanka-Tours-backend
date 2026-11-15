"""`python -m src.scripts.set_admin_password <email>`: set an admin's password from a shell."""
from src.core.security import verify_password
from src.models.admin import AdminUser, PasswordToken
from src.scripts.set_admin_password import main
from src.services.admin_bootstrap import issue_password_link
from tests.conftest import ADMIN_TEST_EMAIL

NEW = "a-brand-new-password"


def _prompts(*answers):
    answers = list(answers)
    return lambda prompt="": answers.pop(0)


def test_sets_password_and_allows_login(client, db, session_factory, admin_user, capsys):
    code = main([" Admin@Example.com "], getpass=_prompts(NEW, NEW), session_factory=session_factory)
    assert code == 0
    db.refresh(admin_user)
    assert verify_password(NEW, admin_user.password_hash)
    r = client.post("/api/admin/auth/login", json={"email": ADMIN_TEST_EMAIL, "password": NEW})
    assert r.status_code == 200
    assert NEW not in capsys.readouterr().out


def test_signs_out_sessions_and_voids_pending_links(client, db, session_factory, admin_user, admin_headers):
    link = issue_password_link(db, admin_user, "set")
    assert main([ADMIN_TEST_EMAIL], getpass=_prompts(NEW, NEW), session_factory=session_factory) == 0
    assert client.get("/api/admin/auth/me", headers=admin_headers).status_code == 401
    token = link.split("token=", 1)[1]
    r = client.post("/api/admin/auth/set-password", json={"token": token, "password": "yet-another-password"})
    assert r.status_code == 400
    assert db.query(PasswordToken).filter(PasswordToken.used_at.is_(None)).count() == 0


def test_mismatched_passwords_change_nothing(db, session_factory, admin_user):
    before = admin_user.password_hash
    assert main([ADMIN_TEST_EMAIL], getpass=_prompts(NEW, NEW + "x"), session_factory=session_factory) == 1
    db.refresh(admin_user)
    assert admin_user.password_hash == before


def test_short_password_rejected(db, session_factory, admin_user):
    assert main([ADMIN_TEST_EMAIL], getpass=_prompts("short", "short"), session_factory=session_factory) == 1


def test_password_over_72_bytes_rejected(db, session_factory, admin_user):
    long_pw = "é" * 40  # 40 characters but 80 bytes; bcrypt would silently cut it
    assert main([ADMIN_TEST_EMAIL], getpass=_prompts(long_pw, long_pw), session_factory=session_factory) == 1


def test_unknown_email_rejected(db, session_factory, capsys):
    assert main(["ghost@example.com"], getpass=_prompts(NEW, NEW), session_factory=session_factory) == 1
    assert "ADMIN_EMAILS" in capsys.readouterr().err
    assert db.query(AdminUser).count() == 0


def test_inactive_admin_rejected(db, session_factory, admin_user):
    admin_user.is_active = False
    db.flush()
    assert main([ADMIN_TEST_EMAIL], getpass=_prompts(NEW, NEW), session_factory=session_factory) == 1


def test_usage_without_email(session_factory, capsys):
    assert main([], getpass=_prompts(), session_factory=session_factory) == 2
    assert "usage" in capsys.readouterr().err.lower()
