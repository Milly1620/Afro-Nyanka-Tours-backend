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


def price_booking(db: Session, booking_in: schemas.BookingCreate, tours: list[models.Tour]) -> PricedBooking:
    """Compute the booking amount server-side and snapshot the chosen extras.

    amount = sum(tour price x people) + sum(extra prices). If any tour has no
    price the amount is None (quoted manually), but extras are still recorded.
    `tours` are the already-validated, visible tours in this booking.
    """
    tour_ids = [t.id for t in tours]
    snapshots: list[models.BookingExtra] = []
    extras_total = 0
    for selection in booking_in.extras:
        tour_id = selection.tour_id
        if tour_id is None and len(tour_ids) == 1:
            tour_id = tour_ids[0]
        if tour_id not in tour_ids:
            raise _unavailable(selection.extra_id)
        price = db.scalar(
            select(models.ExtraPrice)
            .join(models.Extra)
            .where(
                models.ExtraPrice.extra_id == selection.extra_id,
                models.ExtraPrice.tour_id == tour_id,
                models.Extra.is_active.is_(True),
            )
        )
        if price is None:
            raise _unavailable(selection.extra_id)
        snapshots.append(
            models.BookingExtra(
                extra_id=price.extra_id, tour_id=tour_id, name=price.extra.name, price_ghs=price.price_ghs
            )
        )
        extras_total += price.price_ghs

    if any(t.price_ghs is None for t in tours):
        return PricedBooking(amount_ghs=None, extras=snapshots)
    base = sum(t.price_ghs * booking_in.number_of_people for t in tours)
    return PricedBooking(amount_ghs=base + extras_total, extras=snapshots)
