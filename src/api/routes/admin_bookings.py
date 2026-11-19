from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.api.deps import require_admin
from src.crud import crud
from src.database.database import get_db
from src.models import models
from src.schemas.admin_schemas import (
    AdminBookingDetail,
    AdminBookingList,
    AdminBookingListItem,
    BookingStatusUpdate,
)
from src.services.booking_status import BOOKING_STATUSES, booking_display_name, booking_reference, change_status
from src.services.email_service import email_service
from src.services.site_settings import company_context, get_site_settings

# Statuses the customer is emailed about. "paid" is left out: payment is arranged with the customer directly.
CUSTOMER_EMAIL_STATUSES = {"confirmed", "cancelled"}

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_item(b: models.Booking) -> AdminBookingListItem:
    return AdminBookingListItem(
        id=b.id,
        reference=booking_reference(b.id),
        customer_name=b.customer_name,
        customer_email=b.customer_email,
        tour_or_event_name=booking_display_name(b),
        start_date=b.start_date,
        number_of_people=b.number_of_people,
        amount_ghs=b.amount_ghs,
        status=b.status,
        created_at=b.created_at,
    )


def _get_or_404(db: Session, booking_id: int) -> models.Booking:
    booking = db.get(models.Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("", response_model=AdminBookingList)
def list_bookings(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = (
        select(models.Booking)
        .options(
            selectinload(models.Booking.booking_tours).selectinload(models.BookingTour.tour),
            selectinload(models.Booking.event),
        )
        .order_by(models.Booking.created_at.desc(), models.Booking.id.desc())
    )
    if status_filter:
        query = query.where(models.Booking.status == status_filter)
    bookings = db.scalars(query.offset(skip).limit(limit)).all()

    by_status = dict(db.execute(select(models.Booking.status, func.count()).group_by(models.Booking.status)).all())
    counts = {s: by_status.get(s, 0) for s in BOOKING_STATUSES}
    counts["all"] = sum(counts.values())

    items = [_to_item(b) for b in bookings]
    return AdminBookingList(items=items, counts=counts)


@router.get("/{booking_id}", response_model=AdminBookingDetail)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = _get_or_404(db, booking_id)
    return AdminBookingDetail(booking=booking, summary=crud.get_booking_summary(db, booking))


@router.patch("/{booking_id}/status", response_model=AdminBookingListItem)
def update_status(
    booking_id: int,
    body: BookingStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    booking = change_status(db, _get_or_404(db, booking_id), body.status)
    site = get_site_settings(db)
    if booking.status in CUSTOMER_EMAIL_STATUSES and site.notify_booking_confirmation:
        background_tasks.add_task(
            email_service.send_booking_status_update,
            booking,
            crud.get_booking_summary(db, booking),
            booking.status,
            company_context(site),
        )
    return _to_item(booking)
