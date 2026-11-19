import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.api.routes.admin_extras import attach_extra, detach_extra, get_extra_or_404
from src.database.database import get_db
from src.models import models
from src.schemas.admin_schemas import (
    AdminEvent,
    AdminEventCreate,
    AdminEventList,
    AdminEventUpdate,
    AttachExtraRequest,
    clean_countries,
)
from src.schemas.schemas import ImageUploadResponse, MultipleImageUploadResponse, parse_gallery
from src.services.cloudinary_service import cloudinary_service, public_id_from_url
from src.services.events import seats_booked, seats_left
from src.services.locations import replace_locations
from src.services.visibility import PUBLISH_STATUSES, assert_publishable

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])

FIELDS = (
    "name", "description", "countries", "country", "region", "destination", "start_date", "end_date",
    "price_ghs", "capacity", "highlights", "status", "publish_at",
)  # duration_days is not here: it is calculated from the dates


def _get_or_404(db: Session, event_id: int) -> models.Event:
    event = db.get(models.Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _admin(db: Session, event: models.Event, booked: Optional[int] = None) -> AdminEvent:
    out = AdminEvent.model_validate(event)
    out.seats_booked = seats_booked(db, [event.id])[event.id] if booked is None else booked
    out.seats_left = seats_left(event, out.seats_booked)
    return out


def _set_duration(event: models.Event) -> None:
    """Duration is always worked out from the dates, counting both ends: 15th to 17th is 3 days."""
    event.duration_days = (event.end_date - event.start_date).days + 1


def _replace_locations(db: Session, event: models.Event, location_ids: list[int]) -> None:
    replace_locations(db, models.EventLocation, "event_id", event.id, location_ids)


def _save(db: Session, event: models.Event) -> None:
    db.commit()
    db.expire(event)  # reload ordered locations and extras
    db.refresh(event)


@router.get("", response_model=AdminEventList)
def list_events(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(models.Event).order_by(models.Event.start_date.desc(), models.Event.id.desc())
    if status_filter:
        query = query.where(models.Event.status == status_filter)
    events = db.scalars(query.offset(skip).limit(limit)).all()
    booked = seats_booked(db, [e.id for e in events])
    by_status = dict(db.execute(select(models.Event.status, func.count()).group_by(models.Event.status)).all())
    counts = {s: by_status.get(s, 0) for s in PUBLISH_STATUSES}
    counts["all"] = sum(counts.values())
    return AdminEventList(items=[_admin(db, e, booked[e.id]) for e in events], counts=counts)


@router.get("/{event_id}", response_model=AdminEvent)
def get_event(event_id: int, db: Session = Depends(get_db)):
    return _admin(db, _get_or_404(db, event_id))


@router.post("", response_model=AdminEvent, status_code=status.HTTP_201_CREATED)
def create_event(body: AdminEventCreate, db: Session = Depends(get_db)):
    assert_publishable(body.price_ghs, body.status, body.publish_at)
    event = models.Event(**{f: getattr(body, f) for f in FIELDS})
    _set_duration(event)
    db.add(event)
    db.flush()
    _replace_locations(db, event, body.location_ids)
    _save(db, event)
    return _admin(db, event)


def _assert_capacity_covers_bookings(db: Session, event_id: int, capacity: int) -> None:
    # Lock the event row so a booking can't slip in between the count and the save.
    db.execute(select(models.Event.id).where(models.Event.id == event_id).with_for_update())
    booked = seats_booked(db, [event_id])[event_id]
    if capacity < booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{booked} seats are already booked; capacity can't be lower than that",
        )


@router.patch("/{event_id}", response_model=AdminEvent)
def update_event(event_id: int, body: AdminEventUpdate, db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    changes = body.model_dump(exclude_unset=True)
    location_ids = changes.pop("location_ids", None)
    if changes.get("highlights", ...) is None:
        changes["highlights"] = []
    if "countries" in changes or "country" in changes:
        try:
            changes["countries"] = clean_countries(changes.get("countries"), changes.get("country"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        changes["country"] = ", ".join(changes["countries"])
    for field in ("name", "country", "status", "start_date", "end_date"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    if changes.get("capacity") is not None:
        _assert_capacity_covers_bookings(db, event.id, changes["capacity"])
    for field, value in changes.items():
        setattr(event, field, value)
    if event.end_date < event.start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    _set_duration(event)
    if {"status", "price_ghs", "publish_at"} & changes.keys():
        assert_publishable(event.price_ghs, event.status, event.publish_at)
    if location_ids is not None:
        _replace_locations(db, event, location_ids)
    _save(db, event)
    return _admin(db, event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    has_bookings = db.scalar(
        select(func.count()).select_from(models.Booking).where(models.Booking.event_id == event.id)
    )
    if has_bookings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This event has bookings and can't be deleted. Set it to draft to hide it instead.",
        )
    db.execute(delete(models.EventLocation).where(models.EventLocation.event_id == event.id))
    db.execute(delete(models.ExtraPrice).where(models.ExtraPrice.event_id == event.id))
    db.delete(event)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{event_id}/extras/{extra_id}", response_model=AdminEvent)
def attach_event_extra(event_id: int, extra_id: int, body: AttachExtraRequest, db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    attach_extra(db, get_extra_or_404(db, extra_id), body, event_id=event.id)
    db.expire(event)
    return _admin(db, event)


@router.delete("/{event_id}/extras/{extra_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_event_extra(event_id: int, extra_id: int, db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    detach_extra(db, extra_id, event_id=event.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_image(file: UploadFile) -> None:
    if not cloudinary_service.validate_image_file(file):
        raise HTTPException(
            status_code=400, detail="Invalid image file. Please upload a valid image (JPG, PNG, WebP, etc.)"
        )


@router.post("/{event_id}/upload-main-image", response_model=ImageUploadResponse)
def upload_event_main_image(event_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    _require_image(file)
    result = cloudinary_service.upload_image(file, folder=f"afro-nyanka-tours/event-{event.id}/main")
    if not result:
        raise HTTPException(status_code=500, detail="Failed to upload image to cloud storage")
    event.main_image_url = result["url"]
    db.commit()
    return ImageUploadResponse(
        success=True, message="Main image uploaded successfully",
        image_url=result["url"], public_id=result["public_id"], image_details=result,
    )


@router.post("/{event_id}/upload-gallery-images", response_model=MultipleImageUploadResponse)
def upload_event_gallery_images(event_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    gallery = parse_gallery(event.gallery_images)
    uploaded, failed = [], []
    for file in files:
        if not cloudinary_service.validate_image_file(file):
            failed.append(file.filename)
            continue
        result = cloudinary_service.upload_image(file, folder=f"afro-nyanka-tours/event-{event.id}/gallery")
        if not result:
            failed.append(file.filename)
            continue
        if result["url"] not in gallery:
            gallery.append(result["url"])
        uploaded.append({"filename": file.filename, "url": result["url"], "public_id": result["public_id"]})
    event.gallery_images = json.dumps(gallery)
    db.commit()
    return MultipleImageUploadResponse(
        success=bool(uploaded),
        message=f"Uploaded {len(uploaded)} of {len(files)} images",
        uploaded_images=uploaded,
        failed_uploads=failed,
    )


@router.delete("/{event_id}/remove-gallery-image")
def remove_event_gallery_image(event_id: int, image_url: str = Form(...), db: Session = Depends(get_db)):
    event = _get_or_404(db, event_id)
    gallery = parse_gallery(event.gallery_images)
    if image_url not in gallery:
        raise HTTPException(status_code=404, detail="Image not found in this event's gallery")
    gallery.remove(image_url)
    event.gallery_images = json.dumps(gallery)
    db.commit()
    public_id = public_id_from_url(image_url)
    if public_id:
        if not cloudinary_service.delete_image(public_id):
            logger.warning("Removed %s from event %s but Cloudinary delete failed", image_url, event.id)
    return {"success": True, "message": "Image removed from gallery", "remaining_images": gallery}
