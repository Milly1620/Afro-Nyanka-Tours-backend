from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.models import models
from src.services.booking_status import booking_display_name, booking_reference
from src.services.events import seats_booked
from src.services.visibility import visible_filter


def _pct_change(current: int, previous: int) -> Optional[float]:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def get_dashboard_metrics(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    today = date.today()
    Booking = models.Booking

    pending = db.scalar(select(func.count()).where(Booking.status == "pending"))
    pending_7d = db.scalar(
        select(func.count()).where(Booking.status == "pending", Booking.created_at >= now - timedelta(days=7))
    )

    def paid_total(*conditions) -> int:
        return db.scalar(
            select(func.coalesce(func.sum(Booking.amount_ghs), 0)).where(Booking.status == "paid", *conditions)
        )

    revenue = paid_total()
    last_30 = paid_total(Booking.created_at >= now - timedelta(days=30))
    prev_30 = paid_total(
        Booking.created_at >= now - timedelta(days=60), Booking.created_at < now - timedelta(days=30)
    )

    upcoming_events = db.scalars(
        select(models.Event)
        .where(visible_filter(models.Event), models.Event.start_date >= today)
        .order_by(models.Event.start_date, models.Event.id)
    ).all()
    booked = seats_booked(db, [e.id for e in upcoming_events])
    capped = [e for e in upcoming_events if e.capacity]
    total_capacity = sum(e.capacity for e in capped)
    occupancy = round(sum(booked[e.id] for e in capped) / total_capacity * 100, 1) if total_capacity else None

    inquiries = db.scalars(
        select(Booking)
        .where(Booking.status == "pending")
        .options(selectinload(Booking.booking_tours).selectinload(models.BookingTour.tour), selectinload(Booking.event))
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .limit(5)
    ).all()

    activity = db.execute(
        select(models.BookingEvent, Booking.customer_name)
        .join(Booking, Booking.id == models.BookingEvent.booking_id)
        .order_by(models.BookingEvent.created_at.desc(), models.BookingEvent.id.desc())
        .limit(10)
    ).all()

    return {
        "new_inquiries": {"count": pending, "delta_7d": pending_7d},
        "upcoming_departures": {
            "count": len(upcoming_events),
            "next_14d": sum(1 for e in upcoming_events if e.start_date <= today + timedelta(days=14)),
        },
        "revenue_ghs": {"total": revenue, "delta_pct_vs_prev_30d": _pct_change(last_30, prev_30)},
        "avg_occupancy_pct": {"value": occupancy},
        "inquiries": [
            {
                "booking_id": b.id,
                "reference": booking_reference(b.id),
                "customer_name": b.customer_name,
                "tour_or_event_name": booking_display_name(b),
                "number_of_people": b.number_of_people,
                "created_at": b.created_at,
            }
            for b in inquiries
        ],
        "upcoming": [
            {
                "event_id": e.id,
                "name": e.name,
                "start_date": e.start_date,
                "seats_booked": booked[e.id],
                "capacity": e.capacity,
            }
            for e in upcoming_events[:5]
        ],
        "recent_activity": [
            {
                "type": event.type,
                "reference": booking_reference(event.booking_id),
                "customer_name": customer_name,
                "to_status": event.to_status,
                "created_at": event.created_at,
            }
            for event, customer_name in activity
        ],
    }
