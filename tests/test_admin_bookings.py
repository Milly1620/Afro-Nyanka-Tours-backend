from sqlalchemy import select

from src.models import models
from src.services.booking_status import booking_reference
from tests.factories import booking_payload, make_booking, make_tour

BASE = "/api/admin/bookings"


def _events(db, booking_id):
    return db.scalars(
        select(models.BookingEvent).where(models.BookingEvent.booking_id == booking_id).order_by(models.BookingEvent.id)
    ).all()


def test_new_booking_is_pending_with_created_event(client, db):
    tour = make_tour(db)
    r = client.post("/api/bookings/", json=booking_payload(tour))
    assert r.status_code == 200, r.text
    booking = r.json()["booking"]
    assert booking["status"] == "pending"
    assert booking["reference"] == f"BC-{booking['id']}"
    events = _events(db, booking["id"])
    assert [(e.type, e.to_status) for e in events] == [("created", "pending")]


def test_reference_format():
    assert booking_reference(42) == "BC-42"


def test_transition_pending_confirmed_paid(client, db, admin_headers):
    booking = make_booking(db)
    for new in ("confirmed", "paid"):
        r = client.patch(f"{BASE}/{booking.id}/status", json={"status": new}, headers=admin_headers)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == new
    events = _events(db, booking.id)
    assert [(e.from_status, e.to_status) for e in events] == [("pending", "confirmed"), ("confirmed", "paid")]
    assert all(e.type == "status_changed" for e in events)


def test_cancelled_is_terminal_409(client, db, admin_headers):
    booking = make_booking(db, status="cancelled")
    r = client.patch(f"{BASE}/{booking.id}/status", json={"status": "pending"}, headers=admin_headers)
    assert r.status_code == 409


def test_paid_to_pending_409(client, db, admin_headers):
    booking = make_booking(db, status="paid")
    assert client.patch(f"{BASE}/{booking.id}/status", json={"status": "pending"}, headers=admin_headers).status_code == 409


def test_paid_can_be_cancelled(client, db, admin_headers):
    booking = make_booking(db, status="paid")
    assert client.patch(f"{BASE}/{booking.id}/status", json={"status": "cancelled"}, headers=admin_headers).status_code == 200


def test_unknown_status_422(client, db, admin_headers):
    booking = make_booking(db)
    assert client.patch(f"{BASE}/{booking.id}/status", json={"status": "refunded"}, headers=admin_headers).status_code == 422


def test_list_filters_and_counts(client, db, admin_headers):
    tour = make_tour(db, name="Serengeti Migration Safari")
    make_booking(db, tour=tour, customer_name="A", amount_ghs=84000)
    make_booking(db, tour=tour, customer_name="B", status="paid")
    make_booking(db, customer_name="C", status="cancelled")
    body = client.get(BASE, headers=admin_headers).json()
    assert body["counts"] == {"all": 3, "pending": 1, "confirmed": 0, "paid": 1, "cancelled": 1}
    assert [b["customer_name"] for b in body["items"]] == ["C", "B", "A"]
    first_a = [b for b in body["items"] if b["customer_name"] == "A"][0]
    assert first_a["tour_or_event_name"] == "Serengeti Migration Safari"
    assert first_a["amount_ghs"] == 84000
    assert first_a["reference"].startswith("BC-")
    paid = client.get(f"{BASE}?status=paid", headers=admin_headers).json()
    assert [b["customer_name"] for b in paid["items"]] == ["B"]


def test_admin_get_booking_includes_summary(client, db, admin_headers):
    booking = make_booking(db, tour=make_tour(db))
    body = client.get(f"{BASE}/{booking.id}", headers=admin_headers).json()
    assert body["booking"]["reference"] == f"BC-{booking.id}"
    assert body["summary"]["total_tours"] == 1


def test_status_change_requires_admin(client, db):
    booking = make_booking(db)
    assert client.patch(f"{BASE}/{booking.id}/status", json={"status": "confirmed"}).status_code == 401
    assert client.get(BASE).status_code == 401


def test_status_change_unknown_booking_404(client, admin_headers):
    assert client.patch(f"{BASE}/999999/status", json={"status": "confirmed"}, headers=admin_headers).status_code == 404
