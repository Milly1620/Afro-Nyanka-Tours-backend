"""Regression tests for the final branch review's findings."""
import pytest
from sqlalchemy import select

from src.core.config import Settings
from src.models.admin import AdminUser
from src.services.admin_bootstrap import issue_password_link, sync_admins
from src.services.rate_limit import LoginRateLimiter
from tests.conftest import ADMIN_TEST_EMAIL, ADMIN_TEST_PASSWORD
from tests.factories import booking_payload, make_extra, make_tour, price_extra

LOGIN = "/api/admin/auth/login"
GOOD_SECRET = "x" * 32


# Important 1: rate limiter bypass --------------------------------------------

def test_spoofed_forwarded_for_does_not_reset_limit(client, admin_user):
    # Render appends the real client IP last; the client controls the left part.
    for i in range(5):
        r = client.post(
            LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": "nope"},
            headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.9"},
        )
        assert r.status_code == 401
    r = client.post(
        LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD},
        headers={"X-Forwarded-For": "10.9.9.9, 203.0.113.9"},
    )
    assert r.status_code == 429


def test_per_email_cap_across_ips(client, admin_user):
    for i in range(20):
        client.post(
            LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": "nope"},
            headers={"X-Forwarded-For": f"198.51.100.{i}"},
        )
    r = client.post(
        LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD},
        headers={"X-Forwarded-For": "198.51.100.250"},
    )
    assert r.status_code == 429


def test_attempts_counted_atomically_before_password_check():
    limiter = LoginRateLimiter(max_failures=5)
    for _ in range(5):
        limiter.begin(["k"])  # parallel requests that haven't finished yet
    with pytest.raises(Exception) as exc:
        limiter.begin(["k"])
    assert getattr(exc.value, "status_code", None) == 429


def test_success_does_not_count_as_failure():
    limiter = LoginRateLimiter(max_failures=2)
    for _ in range(5):
        limiter.begin(["k"])
        limiter.succeed(["k"])
    limiter.begin(["k"])


def test_expired_keys_are_dropped(monkeypatch):
    from src.services import rate_limit

    clock = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])
    limiter = LoginRateLimiter(max_failures=5, window_seconds=60)
    for i in range(50):
        limiter.begin([f"spoof-{i}"])
    clock[0] += 61
    limiter.begin(["fresh"])
    assert set(limiter._failures) == {"fresh"}


# Important 2: empty/short SECRET_KEY ------------------------------------------

@pytest.mark.parametrize("secret", ["", "short-secret"])
def test_empty_or_short_secret_rejected_in_prod(secret):
    with pytest.raises(ValueError):
        Settings(_env_file=None, DATABASE_URL="x", debug=False, secret_key=secret)


def test_long_secret_accepted_in_prod():
    Settings(_env_file=None, DATABASE_URL="x", debug=False, secret_key=GOOD_SECRET)


# Important 3: tokens survive a password reset ----------------------------------

def test_password_reset_revokes_existing_tokens(client, db, admin_user, admin_headers):
    assert client.get("/api/admin/auth/me", headers=admin_headers).status_code == 200
    link = issue_password_link(db, admin_user, "reset")
    token = link.split("token=", 1)[1]
    assert client.post("/api/admin/auth/set-password", json={"token": token, "password": "brand-new-password"}).status_code == 204
    assert client.get("/api/admin/auth/me", headers=admin_headers).status_code == 401
    r = client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": "brand-new-password"})
    new_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/admin/auth/me", headers=new_headers).status_code == 200


# Re-graded: same extra charged twice ------------------------------------------

def test_same_extra_with_and_without_tour_id_charged_once(client, db):
    tour = make_tour(db, price_ghs=100)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour, price_ghs=50)
    body = booking_payload(tour, number_of_people=1, extras=[{"extra_id": extra.id}, {"extra_id": extra.id, "tour_id": tour.id}])
    assert client.post("/api/bookings/", json=body).status_code == 422


# Re-graded: empty FRONTEND_URL --------------------------------------------------

def test_empty_frontend_url_rejected_in_prod():
    with pytest.raises(ValueError):
        Settings(_env_file=None, DATABASE_URL="x", debug=False, secret_key=GOOD_SECRET, frontend_url="  ")


def _request(headers: dict, client_host="10.1.1.1"):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 1234),
    }
    return Request(scope)


def test_client_ip_uses_rightmost_forwarded_for():
    from src.api.routes.admin_auth import client_ip

    assert client_ip(_request({"X-Forwarded-For": "6.6.6.6, 203.0.113.9"})) == "203.0.113.9"
    assert client_ip(_request({})) == "10.1.1.1"


def test_dockerfile_does_not_trust_all_proxy_headers():
    import pathlib

    dockerfile = (pathlib.Path(__file__).parent.parent / "Dockerfile").read_text()
    assert "--forwarded-allow-ips" not in dockerfile
