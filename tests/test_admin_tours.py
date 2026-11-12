import json

from src.models import models
from tests.factories import attach_location, hours, make_location, make_tour

BASE = "/api/admin/tours"


def _create(client, headers, **overrides):
    body = {"name": "Kumasi Ashanti Experience", "country": "Ghana", "region": "Ashanti"}
    body.update(overrides)
    return client.post(BASE, json=body, headers=headers)


def test_admin_tours_require_admin(client):
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json={}).status_code == 401


def test_admin_list_includes_drafts_with_counts(client, db, admin_headers):
    make_tour(db, name="Live")
    make_tour(db, name="Draft", status="draft")
    make_tour(db, name="Later", status="scheduled", publish_at=hours(5))
    body = client.get(BASE, headers=admin_headers).json()
    assert {t["name"] for t in body["items"]} == {"Live", "Draft", "Later"}
    assert body["counts"] == {"all": 3, "published": 1, "draft": 1, "scheduled": 1}
    drafts = client.get(f"{BASE}?status=draft", headers=admin_headers).json()
    assert [t["name"] for t in drafts["items"]] == ["Draft"]
    assert drafts["counts"]["all"] == 3


def test_admin_get_draft_includes_status(client, db, admin_headers):
    draft = make_tour(db, status="draft")
    body = client.get(f"{BASE}/{draft.id}", headers=admin_headers).json()
    assert body["status"] == "draft"
    assert "publish_at" in body


def test_create_published_without_price_422(client, admin_headers):
    assert _create(client, admin_headers, status="published").status_code == 422


def test_create_scheduled_without_publish_at_422(client, admin_headers):
    assert _create(client, admin_headers, status="scheduled", price_ghs=6800).status_code == 422


def test_create_draft_without_price_ok(client, admin_headers):
    r = _create(client, admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft"


def test_create_published_with_price_and_locations(client, db, admin_headers):
    location = make_location(db)
    r = _create(
        client, admin_headers, status="published", price_ghs=6800, duration_days=1,
        capacity=12, highlights=["Guided"], location_ids=[location.id],
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["price_ghs"] == 6800
    assert [tl["location_id"] for tl in body["tour_locations"]] == [location.id]
    assert client.get(f"/api/tours/{body['id']}").status_code == 200


def test_create_rejects_negative_price_and_zero_capacity(client, admin_headers):
    assert _create(client, admin_headers, price_ghs=-1).status_code == 422
    assert _create(client, admin_headers, capacity=0).status_code == 422
    assert _create(client, admin_headers, duration_days=0).status_code == 422


def test_create_unknown_location_422(client, admin_headers):
    assert _create(client, admin_headers, location_ids=[999999]).status_code == 422


def test_edit_grandfathered_unpriced_tour_description_ok(client, db, admin_headers):
    tour = make_tour(db, status="published", price_ghs=None)
    r = client.patch(f"{BASE}/{tour.id}", json={"description": "New copy"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["description"] == "New copy"


def test_patch_status_to_published_requires_price(client, db, admin_headers):
    tour = make_tour(db, status="draft")
    r = client.patch(f"{BASE}/{tour.id}", json={"status": "published"}, headers=admin_headers)
    assert r.status_code == 422
    r = client.patch(f"{BASE}/{tour.id}", json={"status": "published", "price_ghs": 3200}, headers=admin_headers)
    assert r.status_code == 200, r.text


def test_patch_clearing_price_on_published_422(client, db, admin_headers):
    tour = make_tour(db, status="published", price_ghs=3200)
    r = client.patch(f"{BASE}/{tour.id}", json={"price_ghs": None}, headers=admin_headers)
    assert r.status_code == 422


def test_patch_location_ids_replaces_stops_in_order(client, db, admin_headers):
    tour = make_tour(db)
    a, b = make_location(db, name="A"), make_location(db, name="B")
    attach_location(db, tour, a)
    r = client.patch(f"{BASE}/{tour.id}", json={"location_ids": [b.id, a.id]}, headers=admin_headers)
    assert r.status_code == 200, r.text
    stops = sorted(r.json()["tour_locations"], key=lambda tl: tl["order"])
    assert [tl["location_id"] for tl in stops] == [b.id, a.id]


def test_patch_unknown_tour_404(client, admin_headers):
    assert client.patch(f"{BASE}/999999", json={"name": "x"}, headers=admin_headers).status_code == 404


def test_delete_tour_without_bookings_204(client, db, admin_headers):
    tour = make_tour(db)
    attach_location(db, tour, make_location(db))
    r = client.delete(f"{BASE}/{tour.id}", headers=admin_headers)
    assert r.status_code == 204, r.text
    assert db.get(models.Tour, tour.id) is None


def test_delete_tour_with_bookings_409(client, db, admin_headers):
    tour = make_tour(db)
    booking = models.Booking(customer_name="A", customer_email="a@x.com", number_of_people=1)
    db.add(booking)
    db.flush()
    db.add(models.BookingTour(booking_id=booking.id, tour_id=tour.id))
    db.flush()
    r = client.delete(f"{BASE}/{tour.id}", headers=admin_headers)
    assert r.status_code == 409
    assert "draft" in r.json()["detail"].lower()


def test_gallery_images_stored_as_json_text_serialise(client, db):
    tour = make_tour(db, gallery_images=json.dumps(["https://a/x.jpg"]))
    r = client.get(f"/api/tours/{tour.id}")
    assert r.status_code == 200, r.text
    assert r.json()["gallery_images"] == ["https://a/x.jpg"]
