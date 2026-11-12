import threading
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.crud import crud
from src.database.database import engine
from src.models import models
from src.schemas import schemas
from tests.factories import days, make_booking, make_event, make_extra, make_tour, price_extra

URL = "/api/bookings/"


def _payload(event_id, **overrides):
    body = {
        "customer_name": "Millicent Kweku Jones",
        "customer_email": "millie@example.com",
        "number_of_people": 4,
        "event_id": event_id,
    }
    body.update(overrides)
    return body


def test_event_booking_amount_and_dates_from_event(client, db):
    event = make_event(db, price_ghs=42000, start_date=days(30), end_date=days(36))
    extra = make_extra(db)
    price_extra(db, extra, event=event, price_ghs=3500)
    r = client.post(URL, json=_payload(event.id, extras=[{"extra_id": extra.id}], start_date="2020-01-01T00:00:00"))
    assert r.status_code == 200, r.text
    booking = db.get(models.Booking, r.json()["booking"]["id"])
    assert booking.amount_ghs == 42000 * 4 + 3500
    assert booking.event_id == event.id
    assert booking.start_date == datetime.combine(days(30), datetime.min.time())
    assert booking.end_date == datetime.combine(days(36), datetime.min.time())


def test_event_extra_must_belong_to_event(client, db):
    event, tour = make_event(db), make_tour(db)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour)
    r = client.post(URL, json=_payload(event.id, extras=[{"extra_id": extra.id}]))
    assert r.status_code == 400


def test_unpriced_event_booking_null_amount(client, db):
    event = make_event(db, price_ghs=None)
    r = client.post(URL, json=_payload(event.id))
    assert r.status_code == 200, r.text
    assert r.json()["booking"]["amount_ghs"] is None


def test_unlimited_event_never_full(client, db):
    event = make_event(db, capacity=None)
    make_booking(db, event_id=event.id, number_of_people=500)
    assert client.post(URL, json=_payload(event.id, number_of_people=100)).status_code == 200


def test_over_capacity_409_with_seats_left_message(client, db):
    event = make_event(db, capacity=10)
    make_booking(db, event_id=event.id, number_of_people=4, status="pending")
    make_booking(db, event_id=event.id, number_of_people=3, status="paid")
    r = client.post(URL, json=_payload(event.id, number_of_people=4))
    assert r.status_code == 409
    assert r.json()["detail"] == "Only 3 seats left"
    assert client.post(URL, json=_payload(event.id, number_of_people=3)).status_code == 200


def test_cancel_frees_seats(client, db, admin_headers):
    event = make_event(db, capacity=4)
    held = make_booking(db, event_id=event.id, number_of_people=4)
    assert client.post(URL, json=_payload(event.id, number_of_people=1)).status_code == 409
    client.patch(f"/api/admin/bookings/{held.id}/status", json={"status": "cancelled"}, headers=admin_headers)
    assert client.post(URL, json=_payload(event.id, number_of_people=4)).status_code == 200


def test_past_event_booking_400(client, db):
    event = make_event(db, start_date=days(-1), end_date=days(1))
    assert client.post(URL, json=_payload(event.id)).status_code == 400


def test_draft_event_booking_400(client, db):
    event = make_event(db, status="draft")
    assert client.post(URL, json=_payload(event.id)).status_code == 400


def test_both_event_and_tours_422(client, db):
    event, tour = make_event(db), make_tour(db)
    body = _payload(event.id, tour_selections=[{"tour_id": tour.id, "locations": [], "order": 1}])
    assert client.post(URL, json=body).status_code == 422


def test_neither_422(client):
    assert client.post(URL, json=_payload(None)).status_code == 422


def test_negative_people_cannot_free_seats(client, db):
    event = make_event(db, capacity=2)
    make_booking(db, event_id=event.id, number_of_people=2)
    assert client.post(URL, json=_payload(event.id, number_of_people=-5)).status_code == 422


def test_event_booking_summary_and_emails_include_event(client, db, sent_emails):
    event = make_event(db, name="Homowo Festival 2026", destination="Accra, Ghana")
    r = client.post(URL, json=_payload(event.id))
    summary = r.json()["summary"]
    assert summary["event"]["name"] == "Homowo Festival 2026"
    assert summary["event"]["start_date"] == str(event.start_date)
    assert "Homowo Festival 2026" in r.json()["message"]
    assert len(sent_emails) == 2
    for email in sent_emails:
        assert "Homowo Festival 2026" in email["html"]
        assert event.start_date.strftime("%B %d, %Y") in email["html"]


def test_admin_list_shows_event_name(client, db, admin_headers):
    event = make_event(db, name="Homowo Festival 2026")
    make_booking(db, event_id=event.id)
    items = client.get("/api/admin/bookings", headers=admin_headers).json()["items"]
    assert items[0]["tour_or_event_name"] == "Homowo Festival 2026"


def test_concurrent_last_seats(monkeypatch):
    # Force both requests to overlap: after counting seats, each waits (up to 1s)
    # for the other to have counted too. Without the row lock both count 0 and
    # both succeed; with it, the second can't count until the first commits.
    counted = threading.Barrier(2)
    real_seats_booked = crud.seats_booked

    def seats_booked_then_wait(db, event_ids):
        result = real_seats_booked(db, event_ids)
        try:
            counted.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return result

    monkeypatch.setattr(crud, "seats_booked", seats_booked_then_wait)

    with Session(engine) as setup:
        event = models.Event(
            name="Race", country="Ghana", start_date=days(5), end_date=days(6),
            price_ghs=100, capacity=4, status="published",
        )
        setup.add(event)
        setup.commit()
        event_id = event.id

    barrier = threading.Barrier(2)
    outcomes = []

    def worker():
        booking = schemas.BookingCreate(
            customer_name="Racer", customer_email="race@example.com", number_of_people=3, event_id=event_id,
        )
        with Session(engine) as session:
            barrier.wait()
            try:
                crud.create_booking(session, booking)
                outcomes.append("ok")
            except HTTPException as exc:
                outcomes.append(exc.status_code)

    try:
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(outcomes, key=str) == [409, "ok"]
    finally:
        with engine.begin() as conn:
            ids = [r[0] for r in conn.execute(models.Booking.__table__.select().with_only_columns(models.Booking.id).where(models.Booking.event_id == event_id))]
            conn.execute(delete(models.BookingEvent).where(models.BookingEvent.booking_id.in_(ids)))
            conn.execute(delete(models.Booking).where(models.Booking.event_id == event_id))
            conn.execute(delete(models.Event).where(models.Event.id == event_id))
