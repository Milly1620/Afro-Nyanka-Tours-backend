from sqlalchemy import select

from src.models import models
from tests.factories import booking_payload, make_extra, make_tour, price_extra

URL = "/api/bookings/"


def _book(client, tour, **overrides):
    return client.post(URL, json=booking_payload(tour, **overrides))


def _stored(db, response):
    return db.get(models.Booking, response.json()["booking"]["id"])


def test_amount_tours_times_people_plus_extras(client, db):
    tour = make_tour(db, price_ghs=12000)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour, price_ghs=3500)
    r = _book(client, tour, number_of_people=4, extras=[{"extra_id": extra.id, "tour_id": tour.id}])
    assert r.status_code == 200, r.text
    assert r.json()["booking"]["amount_ghs"] == 51500
    assert _stored(db, r).amount_ghs == 51500


def test_multi_tour_amount(client, db):
    a, b = make_tour(db, name="A", price_ghs=1000), make_tour(db, name="B", price_ghs=2000)
    body = booking_payload(a, number_of_people=3)
    body["tour_selections"].append({"tour_id": b.id, "locations": [], "order": 2})
    r = client.post(URL, json=body)
    assert r.json()["booking"]["amount_ghs"] == 9000


def test_extra_tour_id_inferred_for_single_tour(client, db):
    tour = make_tour(db, price_ghs=100)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour, price_ghs=50)
    r = _book(client, tour, number_of_people=1, extras=[{"extra_id": extra.id}])
    assert r.status_code == 200, r.text
    assert r.json()["booking"]["amount_ghs"] == 150


def test_extras_snapshotted_on_booking(client, db):
    tour = make_tour(db, price_ghs=100)
    extra = make_extra(db, name="Private guide")
    price_extra(db, extra, tour=tour, price_ghs=2450)
    r = _book(client, tour, extras=[{"extra_id": extra.id, "tour_id": tour.id}])
    rows = db.scalars(select(models.BookingExtra).where(models.BookingExtra.booking_id == r.json()["booking"]["id"])).all()
    assert [(row.name, row.price_ghs, row.tour_id) for row in rows] == [("Private guide", 2450, tour.id)]
    assert r.json()["summary"]["extras"] == [{"name": "Private guide", "price_ghs": 2450}]


def test_client_total_ignored(client, db):
    tour = make_tour(db, price_ghs=12000)
    r = _book(client, tour, number_of_people=1, amount_ghs=1)
    assert r.json()["booking"]["amount_ghs"] == 12000


def test_unpriced_tour_booking_succeeds_with_null_amount(client, db):
    tour = make_tour(db, price_ghs=None)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour)
    r = _book(client, tour, extras=[{"extra_id": extra.id, "tour_id": tour.id}])
    assert r.status_code == 200, r.text
    assert r.json()["booking"]["amount_ghs"] is None
    assert r.json()["summary"]["extras"][0]["price_ghs"] == 3500


def test_price_change_after_booking_does_not_change_booking(client, db):
    tour = make_tour(db, price_ghs=12000)
    extra = make_extra(db)
    row = price_extra(db, extra, tour=tour, price_ghs=3500)
    r = _book(client, tour, number_of_people=1, extras=[{"extra_id": extra.id}])
    tour.price_ghs = 99999
    row.price_ghs = 99999
    db.flush()
    stored = _stored(db, r)
    db.refresh(stored)
    assert stored.amount_ghs == 15500
    snapshot = db.scalars(select(models.BookingExtra).where(models.BookingExtra.booking_id == stored.id)).one()
    assert snapshot.price_ghs == 3500


def test_inactive_extra_400(client, db):
    tour = make_tour(db, price_ghs=100)
    extra = make_extra(db, is_active=False)
    price_extra(db, extra, tour=tour)
    r = _book(client, tour, extras=[{"extra_id": extra.id, "tour_id": tour.id}])
    assert r.status_code == 400
    assert r.json()["detail"] == f"Extra {extra.id} is not available for this booking"


def test_extra_not_attached_400(client, db):
    tour, other = make_tour(db, price_ghs=100), make_tour(db, name="Other", price_ghs=100)
    extra = make_extra(db)
    price_extra(db, extra, tour=other)
    r = _book(client, tour, extras=[{"extra_id": extra.id, "tour_id": tour.id}])
    assert r.status_code == 400


def test_extra_for_tour_not_in_booking_400(client, db):
    tour, other = make_tour(db, price_ghs=100), make_tour(db, name="Other", price_ghs=100)
    extra = make_extra(db)
    price_extra(db, extra, tour=other)
    r = _book(client, tour, extras=[{"extra_id": extra.id, "tour_id": other.id}])
    assert r.status_code == 400


def test_draft_tour_booking_400(client, db):
    tour = make_tour(db, status="draft", price_ghs=100)
    assert _book(client, tour).status_code == 400


def test_group_larger_than_capacity_400(client, db):
    tour = make_tour(db, price_ghs=100, capacity=3)
    r = _book(client, tour, number_of_people=4)
    assert r.status_code == 400
    assert _book(client, tour, number_of_people=3).status_code == 200


def test_zero_or_negative_people_422(client, db):
    tour = make_tour(db, price_ghs=100)
    assert _book(client, tour, number_of_people=0).status_code == 422
    assert _book(client, tour, number_of_people=-100).status_code == 422


def test_duplicate_extra_422(client, db):
    tour = make_tour(db, price_ghs=100)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour)
    selection = {"extra_id": extra.id, "tour_id": tour.id}
    assert _book(client, tour, extras=[selection, selection]).status_code == 422


def test_http_errors_not_wrapped_as_500(client, db):
    tour = make_tour(db, price_ghs=100)
    r = _book(client, tour, extras=[{"extra_id": 999999, "tour_id": tour.id}])
    assert r.status_code == 400, r.text


def test_emails_include_reference_and_total(client, db, sent_emails):
    tour = make_tour(db, price_ghs=12000)
    r = _book(client, tour, number_of_people=1)
    ref = f"BC-{r.json()['booking']['id']}"
    assert len(sent_emails) == 2
    for email in sent_emails:
        assert ref in email["html"]
        assert "GHS 12,000" in email["html"]


def test_emails_say_price_to_be_confirmed_when_unpriced(client, db, sent_emails):
    tour = make_tour(db, price_ghs=None)
    _book(client, tour)
    assert all("Price to be confirmed" in e["html"] for e in sent_emails)
