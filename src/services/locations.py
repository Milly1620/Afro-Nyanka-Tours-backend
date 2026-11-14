from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models import models


def replace_locations(db: Session, link_model, owner_field: str, owner_id: int, location_ids: list[int]) -> None:
    """Replace a tour's or event's ordered locations (`link_model` is TourLocation or EventLocation)."""
    if len(set(location_ids)) != len(location_ids):
        raise HTTPException(status_code=422, detail="Duplicate location ids")
    if location_ids:
        found = set(db.scalars(select(models.Location.id).where(models.Location.id.in_(location_ids))))
        missing = [i for i in location_ids if i not in found]
        if missing:
            raise HTTPException(status_code=422, detail=f"Unknown location ids: {missing}")
    db.execute(delete(link_model).where(getattr(link_model, owner_field) == owner_id))
    for order, location_id in enumerate(location_ids, start=1):
        db.add(link_model(**{owner_field: owner_id, "location_id": location_id, "order": order}))
