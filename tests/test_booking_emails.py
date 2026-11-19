"""Customer booking emails: 'pending' on submit, then confirmed / cancelled from the admin page."""
from src.services.site_settings import get_site_settings
from tests.factories import booking_payload, make_event, make_tour

STATUS = "/api/admin/bookings/{}/status"


def _customer_emails(sent, email="millie@example.com"):
    return [m for m in sent if m["to"] == email]


def _book_tours(client, db):
    tour_a = make_tour(db, name="Cape Coast Heritage", price_ghs=100)
    tour_b = make_tour(db, name="Mole Safari", price_ghs=200)
    body = booking_payload(tour_a)
    body["tour_selections"].append({"tour_id": tour_b.id, "locations": [], "order": 2})
    r = client.post("/api/bookings/", json=body)
    assert r.status_code == 200, r.text
    return r.json()["booking"]["id"]


def test_new_tour_booking_email_says_confirmation_pending(client, db, sent_emails):
    _book_tours(client, db)
    [mail] = _customer_emails(sent_emails)
    assert mail["subject"] == "Multi-Tour Booking Confirmation Pending - 2 Tours Selected"
    assert "<h2>Multi-Tour Booking Confirmation Pending</h2>" in mail["html"]


def test_new_event_booking_email_says_confirmation_pending(client, db, sent_emails):
    event = make_event(db)
    body = {"customer_name": "Millicent Kweku Jones", "customer_email": "millie@example.com",
            "number_of_people": 2, "event_id": event.id}
    assert client.post("/api/bookings/", json=body).status_code == 200
    [mail] = _customer_emails(sent_emails)
    assert mail["subject"] == f"Booking Confirmation Pending - {event.name}"
    assert "<h2>Booking Confirmation Pending</h2>" in mail["html"]
    assert "Multi-Tour" not in mail["html"]


def test_confirming_booking_emails_customer(client, db, admin_headers, sent_emails):
    booking_id = _book_tours(client, db)
    sent_emails.clear()
    assert client.patch(STATUS.format(booking_id), json={"status": "confirmed"}, headers=admin_headers).status_code == 200
    [mail] = _customer_emails(sent_emails)
    assert mail["subject"] == "Multi-Tour Booking Confirmation - 2 Tours Selected"
    assert "<h2>Multi-Tour Booking Confirmation</h2>" in mail["html"]
    assert f"BC-{booking_id}" in mail["html"]


def test_cancelling_booking_emails_customer(client, db, admin_headers, sent_emails):
    booking_id = _book_tours(client, db)
    sent_emails.clear()
    assert client.patch(STATUS.format(booking_id), json={"status": "cancelled"}, headers=admin_headers).status_code == 200
    [mail] = _customer_emails(sent_emails)
    assert mail["subject"] == "Multi-Tour Booking Cancelled - 2 Tours Selected"
    assert "<h2>Multi-Tour Booking Cancelled</h2>" in mail["html"]


def test_marking_paid_sends_no_email(client, db, admin_headers, sent_emails):
    booking_id = _book_tours(client, db)
    sent_emails.clear()
    assert client.patch(STATUS.format(booking_id), json={"status": "paid"}, headers=admin_headers).status_code == 200
    assert _customer_emails(sent_emails) == []


def test_status_emails_follow_confirmation_toggle(client, db, admin_headers, sent_emails):
    booking_id = _book_tours(client, db)
    get_site_settings(db).notify_booking_confirmation = False
    db.flush()
    sent_emails.clear()
    assert client.patch(STATUS.format(booking_id), json={"status": "confirmed"}, headers=admin_headers).status_code == 200
    assert _customer_emails(sent_emails) == []


def test_rejected_status_change_sends_no_email(client, db, admin_headers, sent_emails):
    booking_id = _book_tours(client, db)
    client.patch(STATUS.format(booking_id), json={"status": "cancelled"}, headers=admin_headers)
    sent_emails.clear()
    assert client.patch(STATUS.format(booking_id), json={"status": "confirmed"}, headers=admin_headers).status_code == 409
    assert sent_emails == []
