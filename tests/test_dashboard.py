from datetime import datetime, timedelta, timezone

from src.models import models
from src.services.dashboard import get_dashboard_metrics
from tests.factories import days, make_booking, make_event, make_tour

URL = "/api/admin/dashboard"


def ago(n_days: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n_days)


def test_dashboard_requires_admin(client):
    assert client.get(URL).status_code == 401


def test_revenue_counts_only_paid(db):
    make_booking(db, status="paid", amount_ghs=1000)
    make_booking(db, status="paid", amount_ghs=2500)
    make_booking(db, status="confirmed", amount_ghs=9999)
    make_booking(db, status="cancelled", amount_ghs=9999)
    make_booking(db, status="paid", amount_ghs=None)
    assert get_dashboard_metrics(db)["revenue_ghs"]["total"] == 3500


def test_revenue_delta_vs_previous_30_days(db):
    make_booking(db, status="paid", amount_ghs=1500, created_at=ago(5))
    make_booking(db, status="paid", amount_ghs=1000, created_at=ago(40))
    assert get_dashboard_metrics(db)["revenue_ghs"]["delta_pct_vs_prev_30d"] == 50.0


def test_revenue_delta_null_when_no_previous(db):
    make_booking(db, status="paid", amount_ghs=1500, created_at=ago(5))
    assert get_dashboard_metrics(db)["revenue_ghs"]["delta_pct_vs_prev_30d"] is None


def test_new_inquiries_count_and_delta(db):
    make_booking(db, created_at=ago(2))
    make_booking(db, created_at=ago(20))
    make_booking(db, status="confirmed", created_at=ago(1))
    assert get_dashboard_metrics(db)["new_inquiries"] == {"count": 2, "delta_7d": 1}


def test_upcoming_departures(db):
    make_event(db, start_date=days(3), end_date=days(4))
    make_event(db, start_date=days(30), end_date=days(31))
    make_event(db, start_date=days(-3), end_date=days(-2))
    make_event(db, start_date=days(5), end_date=days(6), status="draft")
    assert get_dashboard_metrics(db)["upcoming_departures"] == {"count": 2, "next_14d": 1}


def test_occupancy_ignores_unlimited_events(db):
    capped = make_event(db, capacity=10, start_date=days(3), end_date=days(4))
    unlimited = make_event(db, capacity=None, start_date=days(5), end_date=days(6))
    make_booking(db, event_id=capped.id, number_of_people=4)
    make_booking(db, event_id=unlimited.id, number_of_people=50)
    make_booking(db, event_id=capped.id, number_of_people=3, status="cancelled")
    assert get_dashboard_metrics(db)["avg_occupancy_pct"] == {"value": 40.0}


def test_occupancy_null_when_no_capped_events(db):
    make_event(db, capacity=None)
    assert get_dashboard_metrics(db)["avg_occupancy_pct"] == {"value": None}


def test_inquiries_are_newest_pending(db):
    tour = make_tour(db, name="Zanzibar Beach Escape")
    for i in range(7):
        make_booking(db, tour=tour, customer_name=f"P{i}", created_at=ago(10 - i))
    make_booking(db, customer_name="Confirmed", status="confirmed", created_at=ago(0))
    inquiries = get_dashboard_metrics(db)["inquiries"]
    assert [i["customer_name"] for i in inquiries] == ["P6", "P5", "P4", "P3", "P2"]
    assert inquiries[0]["tour_or_event_name"] == "Zanzibar Beach Escape"
    assert inquiries[0]["reference"].startswith("BC-")


def test_upcoming_list_soonest_first_with_seats(db):
    later = make_event(db, name="Later", capacity=10, start_date=days(20), end_date=days(21))
    sooner = make_event(db, name="Sooner", capacity=None, start_date=days(2), end_date=days(3))
    make_booking(db, event_id=later.id, number_of_people=6)
    upcoming = get_dashboard_metrics(db)["upcoming"]
    assert [(u["name"], u["seats_booked"], u["capacity"]) for u in upcoming] == [
        ("Sooner", 0, None), ("Later", 6, 10)
    ]


def test_recent_activity_shows_status_changes(client, db, admin_headers):
    booking = make_booking(db, customer_name="Fatima Bello")
    client.patch(f"/api/admin/bookings/{booking.id}/status", json={"status": "paid"}, headers=admin_headers)
    activity = client.get(URL, headers=admin_headers).json()["recent_activity"]
    assert activity[0] == {
        "type": "status_changed",
        "reference": f"BC-{booking.id}",
        "customer_name": "Fatima Bello",
        "to_status": "paid",
        "created_at": activity[0]["created_at"],
    }


def test_dashboard_endpoint_shape(client, admin_headers):
    body = client.get(URL, headers=admin_headers).json()
    assert set(body) == {
        "new_inquiries", "upcoming_departures", "revenue_ghs", "avg_occupancy_pct",
        "inquiries", "upcoming", "recent_activity",
    }
