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
