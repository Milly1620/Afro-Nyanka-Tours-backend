from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from src.models import models

BOOKING_STATUSES = ("pending", "confirmed", "paid", "cancelled")

ALLOWED = {
    "pending": {"confirmed", "paid", "cancelled"},
    "confirmed": {"paid", "cancelled"},
    "paid": {"cancelled"},
    "cancelled": set(),
}


def booking_reference(booking_id: int) -> str:
    return f"BC-{booking_id}"


def booking_display_name(booking: models.Booking) -> Optional[str]:
    """What the booking is for: the event, or the first tour by order."""
    if booking.event is not None:
        return booking.event.name
    tours = sorted(booking.booking_tours, key=lambda bt: (bt.order or 0, bt.id))
    return tours[0].tour.name if tours else None


def record_created(db: Session, booking: models.Booking) -> None:
    db.add(models.BookingEvent(booking_id=booking.id, type="created", to_status=booking.status or "pending"))


def change_status(db: Session, booking: models.Booking, new_status: str) -> models.Booking:
    current = booking.status
    if new_status not in ALLOWED.get(current, set()):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Can't change a {current} booking to {new_status}",
        )
    booking.status = new_status
    db.add(
        models.BookingEvent(
            booking_id=booking.id, type="status_changed", from_status=current, to_status=new_status
        )
    )
    db.commit()
    db.refresh(booking)
    return booking
