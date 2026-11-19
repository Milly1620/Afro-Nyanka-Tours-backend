"""Country names typed in admin are tidied up; events can be filtered by country."""
import pytest

from src.services.countries import normalise_country
from tests.factories import days, make_event

ADMIN_EVENTS = "/api/admin/events"


@pytest.mark.parametrize("typed, stored", [
    ("ghana", "Ghana"),
    ("  GHANA ", "Ghana"),
    ("burkina faso", "Burkina Faso"),
    ("BURKINA   faso", "Burkina Faso"),
    ("côte d'ivoire", "Côte d'Ivoire"),
    ("cote d'ivoire", "Côte d'Ivoire"),
    ("ivory coast", "Côte d'Ivoire"),
    ("sierra leone", "Sierra Leone"),
    ("south of the river", "South Of The River"),
])
def test_normalise_country(typed, stored):
    assert normalise_country(typed) == stored


def _event(client, headers, **body):
    body = {"name": "Trail", "start_date": str(days(40)), "end_date": str(days(42)), **body}
    return client.post(ADMIN_EVENTS, json=body, headers=headers)


def test_event_countries_capitalised(client, admin_headers):
    r = _event(client, admin_headers, countries=["ghana", "TOGO", "côte d'ivoire", "Ghana"])
    assert r.json()["countries"] == ["Ghana", "Togo", "Côte d'Ivoire"]
    assert r.json()["country"] == "Ghana, Togo, Côte d'Ivoire"


def test_tour_country_capitalised(client, admin_headers):
    r = client.post("/api/admin/tours", json={"name": "Volta", "country": "burkina faso"}, headers=admin_headers)
    assert r.json()["country"] == "Burkina Faso"
    r = client.patch(f"/api/admin/tours/{r.json()['id']}", json={"country": "  togo"}, headers=admin_headers)
    assert r.json()["country"] == "Togo"


def test_location_country_capitalised(client, admin_headers):
    r = client.post("/api/tours/locations/", json={"name": "Grand Popo", "country": "benin"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["country"] == "Benin"


def test_public_events_filtered_by_country(client, db):
    trail = make_event(db, name="Trail", countries=["Ghana", "Togo", "Benin"], country="Ghana, Togo, Benin")
    homowo = make_event(db, name="Homowo", countries=["Ghana"], country="Ghana")
    make_event(db, name="Abidjan Jazz", countries=["Côte d'Ivoire"], country="Côte d'Ivoire")

    def names(query):
        return [e["name"] for e in client.get(f"/api/events/{query}").json()]

    assert set(names("?country=togo")) == {trail.name}
    assert set(names("?country=Ghana")) == {trail.name, homowo.name}
    assert set(names("?country=Benin&country=C%C3%B4te%20d%27Ivoire")) == {trail.name, "Abidjan Jazz"}
    assert set(names("?country=ivory%20coast")) == {"Abidjan Jazz"}
    assert names("?country=Niger") == []
    assert len(names("")) == 3


def test_admin_events_filtered_by_country(client, db, admin_headers):
    make_event(db, name="Trail", countries=["Ghana", "Togo"], country="Ghana, Togo", status="draft")
    make_event(db, name="Ouaga", countries=["Burkina Faso"], country="Burkina Faso")
    body = client.get(f"{ADMIN_EVENTS}?country=togo", headers=admin_headers).json()
    assert [e["name"] for e in body["items"]] == ["Trail"]
