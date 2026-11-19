from src.models import models
from tests.factories import make_extra, make_tour, price_extra

EXTRAS = "/api/admin/extras"


def _public_extras(client, tour):
    return client.get(f"/api/tours/{tour.id}").json()["extras"]


def test_extras_require_admin(client, db):
    tour = make_tour(db)
    extra = make_extra(db)
    assert client.get(EXTRAS).status_code == 401
    assert client.post(EXTRAS, json={"name": "x"}).status_code == 401
    assert client.patch(f"{EXTRAS}/{extra.id}", json={"name": "x"}).status_code == 401
    assert client.put(f"/api/admin/tours/{tour.id}/extras/{extra.id}", json={"price_ghs": 1}).status_code == 401
    assert client.delete(f"/api/admin/tours/{tour.id}/extras/{extra.id}").status_code == 401


def test_create_list_and_update_extra(client, admin_headers):
    r = client.post(EXTRAS, json={"name": "Private guide", "default_price_ghs": 2450}, headers=admin_headers)
    assert r.status_code == 201, r.text
    extra = r.json()
    assert extra["is_active"] is True
    r = client.patch(f"{EXTRAS}/{extra['id']}", json={"description": "Dedicated guide"}, headers=admin_headers)
    assert r.json()["description"] == "Dedicated guide"
    names = [e["name"] for e in client.get(EXTRAS, headers=admin_headers).json()]
    assert "Private guide" in names


def test_extra_negative_default_price_422(client, admin_headers):
    assert client.post(EXTRAS, json={"name": "x", "default_price_ghs": -5}, headers=admin_headers).status_code == 422


def test_no_delete_endpoint_for_extras(client, db, admin_headers):
    extra = make_extra(db)
    assert client.delete(f"{EXTRAS}/{extra.id}", headers=admin_headers).status_code == 405


def test_same_extra_different_price_per_tour(client, db, admin_headers):
    serengeti, zanzibar = make_tour(db, name="Serengeti"), make_tour(db, name="Zanzibar")
    extra = make_extra(db)
    for tour, price in ((serengeti, 3500), (zanzibar, 2000)):
        r = client.put(f"/api/admin/tours/{tour.id}/extras/{extra.id}", json={"price_ghs": price}, headers=admin_headers)
        assert r.status_code == 200, r.text
    assert _public_extras(client, serengeti) == [
        {"extra_id": extra.id, "name": extra.name, "description": extra.description, "price_ghs": 3500}
    ]
    assert _public_extras(client, zanzibar)[0]["price_ghs"] == 2000


def test_put_updates_existing_price(client, db, admin_headers):
    tour, extra = make_tour(db), make_extra(db)
    url = f"/api/admin/tours/{tour.id}/extras/{extra.id}"
    client.put(url, json={"price_ghs": 3500}, headers=admin_headers)
    client.put(url, json={"price_ghs": 3900}, headers=admin_headers)
    assert [e["price_ghs"] for e in _public_extras(client, tour)] == [3900]


def test_attach_uses_default_price_when_omitted(client, db, admin_headers):
    tour = make_tour(db)
    extra = make_extra(db, default_price_ghs=800)
    r = client.put(f"/api/admin/tours/{tour.id}/extras/{extra.id}", json={}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _public_extras(client, tour)[0]["price_ghs"] == 800


def test_attach_without_any_price_is_price_on_request(client, db, admin_headers):
    tour, extra = make_tour(db), make_extra(db, default_price_ghs=None)
    r = client.put(f"/api/admin/tours/{tour.id}/extras/{extra.id}", json={}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert _public_extras(client, tour)[0]["price_ghs"] is None
    admin = client.get(f"/api/admin/tours/{tour.id}", headers=admin_headers).json()
    assert admin["extras"][0]["price_ghs"] is None


def test_attach_unknown_tour_or_extra_404(client, db, admin_headers):
    tour, extra = make_tour(db), make_extra(db)
    assert client.put(f"/api/admin/tours/999999/extras/{extra.id}", json={"price_ghs": 1}, headers=admin_headers).status_code == 404
    assert client.put(f"/api/admin/tours/{tour.id}/extras/999999", json={"price_ghs": 1}, headers=admin_headers).status_code == 404


def test_inactive_extra_hidden_publicly_but_kept_in_admin(client, db, admin_headers):
    tour, extra = make_tour(db), make_extra(db)
    price_extra(db, extra, tour=tour)
    client.patch(f"{EXTRAS}/{extra.id}", json={"is_active": False}, headers=admin_headers)
    assert _public_extras(client, tour) == []
    admin_view = client.get(f"/api/admin/tours/{tour.id}", headers=admin_headers).json()["extras"]
    assert admin_view == [
        {"extra_id": extra.id, "name": extra.name, "description": extra.description, "price_ghs": 3500, "is_active": False}
    ]


def test_detach_removes_from_public_tour(client, db, admin_headers):
    tour, extra = make_tour(db), make_extra(db)
    price_extra(db, extra, tour=tour)
    r = client.delete(f"/api/admin/tours/{tour.id}/extras/{extra.id}", headers=admin_headers)
    assert r.status_code == 204
    assert _public_extras(client, tour) == []
    assert db.get(models.Extra, extra.id) is not None


def test_delete_tour_with_extra_and_location_204(client, db, admin_headers):
    from tests.factories import attach_location, make_location

    tour, extra = make_tour(db), make_extra(db)
    attach_location(db, tour, make_location(db))
    price_extra(db, extra, tour=tour)
    assert client.delete(f"/api/admin/tours/{tour.id}", headers=admin_headers).status_code == 204
    assert db.get(models.Extra, extra.id) is not None
