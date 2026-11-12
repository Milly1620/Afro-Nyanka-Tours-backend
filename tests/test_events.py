from src.models import models
from tests.factories import (
    days, hours, make_booking, make_event, make_extra, make_location, make_tour, price_extra,
)

ADMIN = "/api/admin/events"


def _create(client, headers, **overrides):
    body = {
        "name": "Kilimanjaro Trek", "country": "Tanzania", "destination": "Kilimanjaro",
        "start_date": str(days(40)), "end_date": str(days(46)),
    }
    body.update(overrides)
    return client.post(ADMIN, json=body, headers=headers)


# --- public ----------------------------------------------------------------

def test_upcoming_events_sorted_and_excludes_past(client, db):
    later = make_event(db, name="Later", start_date=days(60), end_date=days(61))
    sooner = make_event(db, name="Sooner", start_date=days(10), end_date=days(11))
    make_event(db, name="Past", start_date=days(-10), end_date=days(-9))
    ongoing = make_event(db, name="Ongoing", start_date=days(-1), end_date=days(1))
    names = [e["name"] for e in client.get("/api/events/").json()]
    assert names == ["Ongoing", "Sooner", "Later"]
    assert {ongoing.id, sooner.id, later.id} == {e["id"] for e in client.get("/api/events/").json()}


def test_draft_and_future_scheduled_events_hidden(client, db):
    draft = make_event(db, name="Draft", status="draft")
    scheduled = make_event(db, name="Soon", status="scheduled", publish_at=hours(2))
    assert client.get("/api/events/").json() == []
    assert client.get(f"/api/events/{draft.id}").status_code == 404
    assert client.get(f"/api/events/{scheduled.id}").status_code == 404


def test_public_event_detail(client, db):
    event = make_event(db, capacity=20, highlights=["Guided Experience"])
    location = make_location(db, name="Jamestown")
    db.add(models.EventLocation(event_id=event.id, location_id=location.id, order=1))
    make_booking(db, event_id=event.id, number_of_people=5)
    make_booking(db, event_id=event.id, number_of_people=3, status="cancelled")
    body = client.get(f"/api/events/{event.id}").json()
    assert body["seats_left"] == 15
    assert body["highlights"] == ["Guided Experience"]
    assert [l["name"] for l in body["locations"]] == ["Jamestown"]
    assert "status" not in body


def test_seats_left_null_when_unlimited(client, db):
    event = make_event(db, capacity=None)
    assert client.get(f"/api/events/{event.id}").json()["seats_left"] is None


def test_event_extras_priced_independently_of_tour(client, db):
    tour, event = make_tour(db), make_event(db)
    extra = make_extra(db)
    price_extra(db, extra, tour=tour, price_ghs=3500)
    price_extra(db, extra, event=event, price_ghs=4200)
    assert client.get(f"/api/events/{event.id}").json()["extras"][0]["price_ghs"] == 4200
    assert client.get(f"/api/tours/{tour.id}").json()["extras"][0]["price_ghs"] == 3500


# --- admin -----------------------------------------------------------------

def test_admin_events_require_admin(client, db):
    event = make_event(db)
    assert client.get(ADMIN).status_code == 401
    assert client.post(ADMIN, json={}).status_code == 401
    assert client.patch(f"{ADMIN}/{event.id}", json={}).status_code == 401
    assert client.delete(f"{ADMIN}/{event.id}").status_code == 401


def test_admin_list_counts_and_seats(client, db, admin_headers):
    event = make_event(db, capacity=10)
    make_event(db, name="Draft", status="draft")
    make_booking(db, event_id=event.id, number_of_people=4)
    body = client.get(ADMIN, headers=admin_headers).json()
    assert body["counts"] == {"all": 2, "published": 1, "draft": 1, "scheduled": 0}
    row = [e for e in body["items"] if e["id"] == event.id][0]
    assert row["seats_booked"] == 4
    assert row["capacity"] == 10


def test_create_event_draft_and_publish_rules(client, admin_headers):
    r = _create(client, admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft"
    assert _create(client, admin_headers, status="published").status_code == 422
    assert _create(client, admin_headers, status="published", price_ghs=55000).status_code == 201


def test_end_before_start_422(client, db, admin_headers):
    assert _create(client, admin_headers, start_date=str(days(10)), end_date=str(days(9))).status_code == 422
    event = make_event(db)
    r = client.patch(f"{ADMIN}/{event.id}", json={"end_date": str(days(1))}, headers=admin_headers)
    assert r.status_code == 422


def test_patch_event_and_locations(client, db, admin_headers):
    event = make_event(db)
    a, b = make_location(db, name="A"), make_location(db, name="B")
    r = client.patch(f"{ADMIN}/{event.id}", json={"name": "Homowo 2026", "location_ids": [b.id, a.id]}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Homowo 2026"
    assert [l["name"] for l in r.json()["locations"]] == ["B", "A"]


def test_delete_event_rules(client, db, admin_headers):
    free = make_event(db, name="Free")
    price_extra(db, make_extra(db), event=free)
    assert client.delete(f"{ADMIN}/{free.id}", headers=admin_headers).status_code == 204
    booked = make_event(db, name="Booked")
    make_booking(db, event_id=booked.id)
    assert client.delete(f"{ADMIN}/{booked.id}", headers=admin_headers).status_code == 409


def test_attach_and_detach_event_extra(client, db, admin_headers):
    event, extra = make_event(db), make_extra(db)
    url = f"{ADMIN}/{event.id}/extras/{extra.id}"
    r = client.put(url, json={"price_ghs": 1200}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["extras"][0]["price_ghs"] == 1200
    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(f"/api/events/{event.id}").json()["extras"] == []


def test_event_image_uploads(client, db, admin_headers, monkeypatch):
    from src.api.routes import admin_events

    event = make_event(db, status="draft")
    monkeypatch.setattr(admin_events.cloudinary_service, "validate_image_file", lambda f: True)
    monkeypatch.setattr(
        admin_events.cloudinary_service, "upload_image",
        lambda file, folder, **k: {"success": True, "url": f"https://img/{folder}.jpg", "public_id": folder},
    )
    monkeypatch.setattr(admin_events.cloudinary_service, "delete_image", lambda public_id: True)
    image = {"file": ("a.jpg", b"\xff\xd8\xff", "image/jpeg")}
    r = client.post(f"{ADMIN}/{event.id}/upload-main-image", files=image, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["image_url"] == f"https://img/afro-nyanka-tours/event-{event.id}/main.jpg"
    r = client.post(f"{ADMIN}/{event.id}/upload-gallery-images", files=[("files", ("b.jpg", b"\xff\xd8\xff", "image/jpeg"))], headers=admin_headers)
    assert r.status_code == 200, r.text
    url = f"https://img/afro-nyanka-tours/event-{event.id}/gallery.jpg"
    assert client.get(f"{ADMIN}/{event.id}", headers=admin_headers).json()["gallery_images"] == [url]
    r = client.request("DELETE", f"{ADMIN}/{event.id}/remove-gallery-image", data={"image_url": url}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert client.get(f"{ADMIN}/{event.id}", headers=admin_headers).json()["gallery_images"] == []
