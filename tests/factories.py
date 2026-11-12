from datetime import datetime, timedelta, timezone

from src.models import models


def make_tour(db, **overrides) -> models.Tour:
    values = dict(name="Cape Coast Heritage", country="Ghana", region="Central", status="published")
    values.update(overrides)
    tour = models.Tour(**values)
    db.add(tour)
    db.flush()
    return tour


def make_location(db, **overrides) -> models.Location:
    values = dict(name="Cape Coast Castle", country="Ghana", region="Central")
    values.update(overrides)
    location = models.Location(**values)
    db.add(location)
    db.flush()
    return location


def attach_location(db, tour, location, order=1) -> models.TourLocation:
    link = models.TourLocation(tour_id=tour.id, location_id=location.id, order=order)
    db.add(link)
    db.flush()
    return link


def hours(n: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=n)


def make_booking(db, tour=None, **overrides) -> models.Booking:
    values = dict(customer_name="Daniel Osei", customer_email="daniel@example.com", number_of_people=2)
    values.update(overrides)
    booking = models.Booking(**values)
    db.add(booking)
    db.flush()
    if tour is not None:
        db.add(models.BookingTour(booking_id=booking.id, tour_id=tour.id, order=1))
        db.flush()
    return booking


def booking_payload(tour, location_ids=(), **overrides) -> dict:
    body = {
        "customer_name": "Millicent Kweku Jones",
        "customer_email": "millie@example.com",
        "number_of_people": 4,
        "tour_selections": [{"tour_id": tour.id, "locations": list(location_ids), "order": 1}],
    }
    body.update(overrides)
    return body


def make_extra(db, **overrides) -> models.Extra:
    values = dict(name="Hot-air balloon safari", description="Sunrise flight over the plains")
    values.update(overrides)
    extra = models.Extra(**values)
    db.add(extra)
    db.flush()
    return extra


def price_extra(db, extra, tour=None, event=None, price_ghs=3500) -> models.ExtraPrice:
    row = models.ExtraPrice(
        extra_id=extra.id,
        tour_id=tour.id if tour else None,
        event_id=event.id if event else None,
        price_ghs=price_ghs,
    )
    db.add(row)
    db.flush()
    return row


def days(n: int):
    from datetime import date, timedelta

    return date.today() + timedelta(days=n)


def make_event(db, **overrides) -> models.Event:
    values = dict(
        name="Homowo Festival 2026", country="Ghana", region="Greater Accra", destination="Accra, Ghana",
        start_date=days(30), end_date=days(32), price_ghs=5000, status="published",
    )
    values.update(overrides)
    event = models.Event(**values)
    db.add(event)
    db.flush()
    return event
