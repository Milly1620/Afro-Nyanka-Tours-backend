import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.database.database import engine
from tests.conftest import alembic_config
from tests.factories import attach_location, hours, make_location, make_tour


def _ids(response):
    return [t["id"] for t in response.json()]


def test_draft_hidden_from_list_and_detail(client, db):
    published = make_tour(db, name="Live")
    draft = make_tour(db, name="Draft", status="draft")
    assert _ids(client.get("/api/tours/")) == [published.id]
    assert client.get(f"/api/tours/{draft.id}").status_code == 404
    assert client.get(f"/api/tours/{published.id}").status_code == 200


def test_scheduled_future_hidden_past_visible(client, db):
    future = make_tour(db, name="Soon", status="scheduled", publish_at=hours(1))
    past = make_tour(db, name="Now", status="scheduled", publish_at=hours(-1 / 60))
    assert _ids(client.get("/api/tours/")) == [past.id]
    assert client.get(f"/api/tours/{future.id}").status_code == 404


def test_country_and_countries_endpoints_respect_visibility(client, db):
    make_tour(db, name="Ghana live", country="Ghana", is_popular=True)
    make_tour(db, name="Togo draft", country="Togo", status="draft", is_popular=True)
    assert client.get("/api/tours/tours/countries").json() == {"countries": ["Ghana"]}
    assert client.get("/api/tours/country/Togo").json() == []
    assert client.get("/api/tours/country/Togo?is_popular=false").json() == []
    assert len(client.get("/api/tours/country/Ghana").json()) == 1


def test_draft_tour_locations_404(client, db):
    draft = make_tour(db, status="draft")
    assert client.get(f"/api/tours/{draft.id}/locations/").status_code == 404


def test_draft_tour_location_detail_404(client, db):
    draft = make_tour(db, status="draft")
    location = make_location(db)
    attach_location(db, draft, location)
    assert client.get(f"/api/tours/{draft.id}/location/{location.id}").status_code == 404


def test_public_tour_exposes_price_fields_not_status(client, db):
    tour = make_tour(db, price_ghs=12000, duration_days=3, capacity=15, highlights=["Guided"])
    body = client.get(f"/api/tours/{tour.id}").json()
    assert body["price_ghs"] == 12000
    assert body["duration_days"] == 3
    assert body["capacity"] == 15
    assert body["highlights"] == ["Guided"]
    assert "status" not in body
    assert "publish_at" not in body


def test_admin_can_add_location_and_mark_popular_on_draft(client, db, admin_headers):
    draft = make_tour(db, status="draft")
    location = make_location(db)
    r = client.post(f"/api/tours/{draft.id}/add-location", json={"location_id": location.id}, headers=admin_headers)
    assert r.status_code == 200, r.text
    r = client.patch(f"/api/tours/tours/popular/{draft.id}", headers=admin_headers)
    assert r.status_code == 200, r.text


def test_admin_image_upload_on_draft_not_404(client, db, admin_headers, monkeypatch):
    from src.api.routes import tours as tours_routes

    draft = make_tour(db, status="draft")
    monkeypatch.setattr(
        tours_routes.cloudinary_service,
        "upload_image",
        lambda *a, **k: {"success": True, "url": "https://img/x.jpg", "public_id": "x"},
    )
    r = client.post(
        f"/api/tours/{draft.id}/upload-main-image",
        files={"file": ("a.jpg", b"\xff\xd8\xff", "image/jpeg")},
        headers=admin_headers,
    )
    assert r.status_code != 404, r.text


@pytest.fixture
def throwaway_db():
    name = f"migtest_{uuid.uuid4().hex[:8]}"
    admin_engine = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    db_engine = create_engine(make_url(engine.url).set(database=name))
    try:
        yield db_engine
    finally:
        db_engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE "{name}"'))
        admin_engine.dispose()


def test_migration_maps_is_active_and_backfills(throwaway_db):
    with throwaway_db.begin() as conn:
        command.upgrade(alembic_config(conn), "0003_admin_users")
        conn.execute(
            text(
                "INSERT INTO tours (name, country, is_active) VALUES "
                "('on', 'Ghana', true), ('off', 'Ghana', false), ('unset', 'Ghana', NULL)"
            )
        )
    with throwaway_db.begin() as conn:
        command.upgrade(alembic_config(conn), "0004_tour_pricing_status")
        rows = dict(conn.execute(text("SELECT name, status FROM tours")).all())
        highlights = conn.execute(text("SELECT DISTINCT highlights::text FROM tours")).scalars().all()
    assert rows == {"on": "published", "off": "draft", "unset": "draft"}
    assert highlights == ["[]"]
