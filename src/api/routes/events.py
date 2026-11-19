from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.models import models
from src.schemas.schemas import PublicEvent
from src.services.countries import event_in_countries
from src.services.events import seats_booked, seats_left
from src.services.visibility import visible_filter

router = APIRouter()


def _public(event: models.Event, booked: int) -> PublicEvent:
    out = PublicEvent.model_validate(event)
    out.seats_left = seats_left(event, booked)
    return out


@router.get("/", response_model=List[PublicEvent])
def list_upcoming_events(
    country: Optional[List[str]] = Query(None, description="Repeat to match any of several: ?country=Ghana&country=Togo"),
    db: Session = Depends(get_db),
):
    query = (
        select(models.Event)
        .where(visible_filter(models.Event), models.Event.end_date >= date.today())
        .order_by(models.Event.start_date, models.Event.id)
    )
    if country:
        query = query.where(event_in_countries(country))
    events = db.scalars(query).all()
    booked = seats_booked(db, [e.id for e in events])
    return [_public(e, booked[e.id]) for e in events]


@router.get("/{event_id}", response_model=PublicEvent)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.scalar(select(models.Event).where(models.Event.id == event_id, visible_filter(models.Event)))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _public(event, seats_booked(db, [event.id])[event.id])
