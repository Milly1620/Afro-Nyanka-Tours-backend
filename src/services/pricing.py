from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import models
from src.schemas import schemas


@dataclass
class PricedBooking:
    amount_ghs: Optional[int]
    extras: list[models.BookingExtra] = field(default_factory=list)


def _unavailable(extra_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Extra {extra_id} is not available for this booking",
    )


def price_booking(
    db: Session,
    booking_in: schemas.BookingCreate,
    tours: list[models.Tour],
    event: Optional[models.Event] = None,
) -> PricedBooking:
    """Compute the booking amount server-side and snapshot the chosen extras.

    amount = sum(offering price x people) + sum(extra prices), where the
    offerings are the booked tours, or the booked event. If any offering has
    no price the amount is None (quoted manually), but extras are still
    recorded. `tours`/`event` are already validated and visible.
    """
    tour_ids = [t.id for t in tours]
    snapshots: list[models.BookingExtra] = []
    extras_total = 0
    seen: set[tuple] = set()
    for selection in booking_in.extras:
        if event is not None:
            if selection.tour_id is not None or selection.event_id not in (None, event.id):
                raise _unavailable(selection.extra_id)
            owner_filter = models.ExtraPrice.event_id == event.id
            tour_id, event_id = None, event.id
        else:
            tour_id = selection.tour_id
            if tour_id is None and len(tour_ids) == 1:
                tour_id = tour_ids[0]
            if tour_id not in tour_ids or selection.event_id is not None:
                raise _unavailable(selection.extra_id)
            owner_filter = models.ExtraPrice.tour_id == tour_id
            event_id = None
        key = (selection.extra_id, tour_id, event_id)
        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Each extra can only be selected once",
            )
        seen.add(key)
        price = db.scalar(
            select(models.ExtraPrice)
            .join(models.Extra)
            .where(
                models.ExtraPrice.extra_id == selection.extra_id,
                owner_filter,
                models.Extra.is_active.is_(True),
            )
        )
        if price is None:
            raise _unavailable(selection.extra_id)
        snapshots.append(
            models.BookingExtra(
                extra_id=price.extra_id, tour_id=tour_id, event_id=event_id,
                name=price.extra.name, price_ghs=price.price_ghs,
            )
        )
        extras_total += price.price_ghs

    offerings = [event] if event is not None else tours
    if any(o.price_ghs is None for o in offerings):
        return PricedBooking(amount_ghs=None, extras=snapshots)
    base = sum(o.price_ghs * booking_in.number_of_people for o in offerings)
    return PricedBooking(amount_ghs=base + extras_total, extras=snapshots)
