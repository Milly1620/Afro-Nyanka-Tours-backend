from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import models


def seats_booked(db: Session, event_ids: Iterable[int]) -> dict[int, int]:
    """People booked per event; cancelled bookings don't hold seats."""
    ids = list(event_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(models.Booking.event_id, func.coalesce(func.sum(models.Booking.number_of_people), 0))
        .where(models.Booking.event_id.in_(ids), models.Booking.status != "cancelled")
        .group_by(models.Booking.event_id)
    ).all()
    booked = {event_id: int(total) for event_id, total in rows}
    return {i: booked.get(i, 0) for i in ids}


def seats_left(event: models.Event, booked: int) -> Optional[int]:
    if event.capacity is None:
        return None
    return max(event.capacity - booked, 0)
