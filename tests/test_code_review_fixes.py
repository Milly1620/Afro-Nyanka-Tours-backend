"""Regression tests for the /code-review findings on feat/admin-portal."""
import pytest
from sqlalchemy import select

from src.core.config import Settings, settings
from src.models import models
from src.models.admin import AdminUser, PasswordToken
from tests.conftest import ADMIN_TEST_EMAIL, ADMIN_TEST_PASSWORD
from tests.factories import booking_payload, make_booking, make_event, make_tour

LOGIN = "/api/admin/auth/login"
FORGOT = "/api/admin/auth/forgot-password"
REPORT = "/api/admin/reports/weekly-summary"
PROD = dict(_env_file=None, DATABASE_URL="x", debug=False, secret_key="x" * 32)
PROD_OK = dict(PROD, frontend_url="https://afronyanka.example", cors_origins="https://afronyanka.example")


# 1. Capacity below seats already booked ------------------------------------------

def test_event_capacity_cannot_drop_below_booked_seats(client, db, admin_headers):
    event = make_event(db, capacity=20)
    make_booking(db, event_id=event.id, number_of_people=18)
    r = client.patch(f"/api/admin/events/{event.id}", json={"capacity": 10}, headers=admin_headers)
    assert r.status_code == 409
    db.refresh(event)
    assert event.capacity == 20


def test_event_capacity_can_drop_to_booked_seats(client, db, admin_headers):
    event = make_event(db, capacity=20)
    make_booking(db, event_id=event.id, number_of_people=18)
    make_booking(db, event_id=event.id, number_of_people=5, status="cancelled")
    r = client.patch(f"/api/admin/events/{event.id}", json={"capacity": 18}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["seats_left"] == 0


# 2. Per-email cap must not lock out the admin's known IP ----------------------------

def test_email_cap_does_not_block_previously_successful_ip(client, admin_user):
    home = {"X-Forwarded-For": "203.0.113.5"}
    assert client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD}, headers=home).status_code == 200
    for i in range(20):
        client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": "nope"},
                    headers={"X-Forwarded-For": f"198.51.100.{i}"})
    attacker = client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD},
                           headers={"X-Forwarded-For": "198.51.100.250"})
    assert attacker.status_code == 429
    r = client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD}, headers=home)
    assert r.status_code == 200


# 3. Production config must not fall back to localhost links --------

def test_default_frontend_url_rejected_in_prod(monkeypatch):
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    with pytest.raises(ValueError, match="FRONTEND_URL"):
        Settings(**dict(PROD, cors_origins="https://afronyanka.example"))


@pytest.mark.parametrize("url", ["http://localhost:3000", "http://127.0.0.1:5173", "  "])
def test_local_frontend_url_rejected_in_prod(url):
    with pytest.raises(ValueError, match="FRONTEND_URL"):
        Settings(**dict(PROD_OK, frontend_url=url))


def test_real_prod_config_accepted():
    s = Settings(**PROD_OK)
    assert s.cors_origin_list == ["https://afronyanka.example"]


def test_debug_still_allows_local_defaults():
    Settings(_env_file=None, DATABASE_URL="x", debug=True)


# 4. Same tour selected twice -------------------------------------------------------

def test_duplicate_tour_selection_rejected(client, db):
    tour = make_tour(db, price_ghs=100)
    body = booking_payload(tour, number_of_people=1)
    body["tour_selections"] = body["tour_selections"] * 2
    assert client.post("/api/bookings/", json=body).status_code == 422
    assert db.scalar(select(models.Booking).where(models.Booking.customer_email == body["customer_email"])) is None


# 5. Forgot-password is rate limited -------------------------------------------------

def test_forgot_password_capped_per_email(client, db, admin_user, sent_emails):
    for i in range(5):
        r = client.post(FORGOT, json={"email": ADMIN_TEST_EMAIL}, headers={"X-Forwarded-For": f"198.51.100.{i}"})
        assert r.status_code == 202
    assert len(sent_emails) == 3
    tokens = db.scalars(select(PasswordToken).where(PasswordToken.admin_id == admin_user.id)).all()
    assert len(tokens) == 3


def test_forgot_password_capped_per_ip(client, sent_emails):
    ip = {"X-Forwarded-For": "203.0.113.77"}
    for i in range(10):
        assert client.post(FORGOT, json={"email": f"ghost{i}@x.com"}, headers=ip).status_code == 202
    assert client.post(FORGOT, json={"email": "ghost-last@x.com"}, headers=ip).status_code == 429


# 6. Weekly summary goes to the active admins and fails loudly ------------------------

def test_weekly_summary_sent_to_active_admins(client, db, admin_user, monkeypatch, sent_emails):
    monkeypatch.setattr(settings, "cron_secret", "right")
    db.add(AdminUser(email="second@example.com", password_hash=None))
    db.add(AdminUser(email="gone@example.com", is_active=False))
    db.flush()
    r = client.post(REPORT, headers={"X-Cron-Secret": "right"})
    assert r.status_code == 200
    assert sorted(e["to"] for e in sent_emails) == [ADMIN_TEST_EMAIL, "second@example.com"]


def test_weekly_summary_with_no_admins_is_an_error(client, monkeypatch, sent_emails):
    monkeypatch.setattr(settings, "cron_secret", "right")
    assert client.post(REPORT, headers={"X-Cron-Secret": "right"}).status_code == 503
    assert sent_emails == []


def test_weekly_summary_send_failure_is_an_error(client, admin_user, monkeypatch):
    from src.services.email_service import email_service

    monkeypatch.setattr(settings, "cron_secret", "right")
    monkeypatch.setattr(email_service, "send_email", lambda *a, **k: False)
    assert client.post(REPORT, headers={"X-Cron-Secret": "right"}).status_code == 502


# 7. Legacy POST /api/tours/ honours is_active -----------------------------------------

def test_legacy_create_active_priced_tour_is_published(client, admin_headers):
    r = client.post("/api/tours/", json={"name": "Cape Coast", "country": "Ghana", "price_ghs": 900}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["id"] in [t["id"] for t in client.get("/api/tours/").json()]
    assert r.json()["price_ghs"] == 900


def test_legacy_create_inactive_tour_is_draft(client, admin_headers):
    r = client.post("/api/tours/", json={"name": "Hidden", "country": "Ghana", "is_active": False}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    assert r.json()["id"] not in [t["id"] for t in client.get("/api/tours/").json()]


def test_legacy_create_active_unpriced_tour_published(client, admin_headers):
    """Tour prices are optional: an unpriced tour is "price on request"."""
    r = client.post("/api/tours/", json={"name": "No price", "country": "Ghana"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["price_ghs"] is None and r.json()["is_active"] is True


def test_admin_status_change_keeps_is_active_in_sync(client, db, admin_headers):
    tour = make_tour(db, price_ghs=100, status="published", is_active=True)
    client.patch(f"/api/admin/tours/{tour.id}", json={"status": "draft"}, headers=admin_headers)
    db.refresh(tour)
    assert tour.is_active is False


# 8. X-Forwarded-For only trusted when configured --------------------------------------

def test_forwarded_for_ignored_without_trusted_proxy(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    for i in range(5):
        client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": "nope"},
                    headers={"X-Forwarded-For": f"10.0.0.{i}"})
    r = client.post(LOGIN, json={"email": ADMIN_TEST_EMAIL, "password": ADMIN_TEST_PASSWORD},
                    headers={"X-Forwarded-For": "10.0.0.99"})
    assert r.status_code == 429


# 9. One Cloudinary public_id parser ----------------------------------------------------

@pytest.mark.parametrize("url, expected", [
    ("https://res.cloudinary.com/demo/image/upload/v1712345678/afro-nyanka-tours/event-3/gallery/abc.jpg",
     "afro-nyanka-tours/event-3/gallery/abc"),
    ("https://res.cloudinary.com/demo/image/upload/afro-nyanka-tours/tour-1/main/xyz.png",
     "afro-nyanka-tours/tour-1/main/xyz"),
    ("https://example.com/not-cloudinary.jpg", None),
])
def test_public_id_from_url(url, expected):
    from src.services.cloudinary_service import public_id_from_url

    assert public_id_from_url(url) == expected
