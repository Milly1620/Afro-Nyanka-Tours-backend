from src.core.config import settings
from src.services.site_settings import get_site_settings
from tests.factories import booking_payload, make_booking, make_tour

ADMIN = "/api/admin/settings"
REPORT = "/api/admin/reports/weekly-summary"


def _book(client, db):
    return client.post("/api/bookings/", json=booking_payload(make_tour(db, price_ghs=100)))


def test_settings_singleton_defaults(db):
    s = get_site_settings(db)
    assert s.id == 1
    assert s.company_name == "Afro Nyanka Tours"
    assert s.contact_email == "info@afronyankatours.com"
    assert (s.notify_new_inquiry, s.notify_booking_confirmation, s.notify_weekly_summary) == (True, True, True)
    assert get_site_settings(db).id == 1


def test_public_settings_hide_toggles(client):
    body = client.get("/api/settings/public").json()
    assert set(body) == {"company_name", "logo_url", "contact_email", "phone", "location"}


def test_update_settings_requires_admin(client):
    assert client.get(ADMIN).status_code == 401
    assert client.put(ADMIN, json={"phone": "+233"}).status_code == 401
    assert client.post(f"{ADMIN}/logo").status_code == 401


def test_admin_update_settings(client, admin_headers):
    r = client.put(ADMIN, json={"phone": "+233 24 123 4567", "location": "Accra, Ghana", "notify_weekly_summary": False}, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = client.get(ADMIN, headers=admin_headers).json()
    assert body["phone"] == "+233 24 123 4567"
    assert body["notify_weekly_summary"] is False
    assert client.get("/api/settings/public").json()["location"] == "Accra, Ghana"


def test_settings_reject_bad_email_and_blank_name(client, admin_headers):
    assert client.put(ADMIN, json={"contact_email": "not-an-email"}, headers=admin_headers).status_code == 422
    assert client.put(ADMIN, json={"company_name": ""}, headers=admin_headers).status_code == 422


def test_logo_upload(client, admin_headers, monkeypatch):
    from src.api.routes import admin_settings

    monkeypatch.setattr(admin_settings.cloudinary_service, "validate_image_file", lambda f: True)
    monkeypatch.setattr(
        admin_settings.cloudinary_service, "upload_image",
        lambda file, folder, **k: {"success": True, "url": f"https://img/{folder}/logo.png", "public_id": "logo"},
    )
    r = client.post(f"{ADMIN}/logo", files={"file": ("l.png", b"\x89PNG", "image/png")}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert client.get("/api/settings/public").json()["logo_url"] == "https://img/afro-nyanka-tours/brand/logo.png"


def test_booking_emails_respect_toggles(client, db, sent_emails):
    s = get_site_settings(db)
    s.notify_new_inquiry = False
    db.flush()
    _book(client, db)
    assert [e["to"] for e in sent_emails] == ["millie@example.com"]

    sent_emails.clear()
    s.notify_new_inquiry, s.notify_booking_confirmation = True, False
    db.flush()
    _book(client, db)
    assert [e["to"] for e in sent_emails] == [settings.admin_email]


def test_email_footer_uses_company_settings(client, db, sent_emails):
    s = get_site_settings(db)
    s.company_name, s.phone = "Nyanka Test Co", "+233 20 000 0000"
    db.flush()
    _book(client, db)
    customer = [e for e in sent_emails if e["to"] == "millie@example.com"][0]
    assert "Nyanka Test Co" in customer["html"]
    assert "+233 20 000 0000" in customer["html"]


def test_weekly_summary_unconfigured_503(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", None)
    assert client.post(REPORT, headers={"X-Cron-Secret": "anything"}).status_code == 503


def test_weekly_summary_wrong_secret_401(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "right")
    assert client.post(REPORT).status_code == 401
    assert client.post(REPORT, headers={"X-Cron-Secret": "wrong"}).status_code == 401


def test_weekly_summary_sends_to_admin(client, db, admin_user, monkeypatch, sent_emails):
    monkeypatch.setattr(settings, "cron_secret", "right")
    make_booking(db, status="paid", amount_ghs=4200)
    r = client.post(REPORT, headers={"X-Cron-Secret": "right"})
    assert r.json() == {"sent": True}
    assert [e["to"] for e in sent_emails] == [admin_user.email]
    assert "GHS 4,200" in sent_emails[0]["html"]


def test_weekly_summary_respects_toggle(client, db, monkeypatch, sent_emails):
    monkeypatch.setattr(settings, "cron_secret", "right")
    get_site_settings(db).notify_weekly_summary = False
    db.flush()
    assert client.post(REPORT, headers={"X-Cron-Secret": "right"}).json() == {"sent": False}
    assert sent_emails == []
