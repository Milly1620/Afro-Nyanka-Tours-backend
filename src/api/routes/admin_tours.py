from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.database.database import get_db
from src.models import analytics, models
from src.api.routes.admin_extras import attach_extra, detach_extra, get_extra_or_404
from src.schemas.admin_schemas import AdminTour, AdminTourCreate, AdminTourList, AdminTourUpdate, AttachExtraRequest
from src.services.locations import replace_locations
from src.services.visibility import PUBLISH_STATUSES, assert_publishable

router = APIRouter(dependencies=[Depends(require_admin)])

NON_LOCATION_FIELDS = (
    "name", "description", "country", "region", "price_ghs", "duration_days",
    "capacity", "highlights", "status", "publish_at", "is_popular",
)


def _get_or_404(db: Session, tour_id: int) -> models.Tour:
    tour = db.get(models.Tour, tour_id)
    if tour is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour not found")
    return tour


def _replace_locations(db: Session, tour: models.Tour, location_ids: list[int]) -> None:
    replace_locations(db, models.TourLocation, "tour_id", tour.id, location_ids)


@router.get("", response_model=AdminTourList)
def list_tours(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    wanted = status_filter
    query = select(models.Tour).order_by(models.Tour.created_at.desc(), models.Tour.id.desc())
    if wanted:
        query = query.where(models.Tour.status == wanted)
    items = db.scalars(query.offset(skip).limit(limit)).all()
    by_status = dict(db.execute(select(models.Tour.status, func.count()).group_by(models.Tour.status)).all())
    counts = {s: by_status.get(s, 0) for s in PUBLISH_STATUSES}
    counts["all"] = sum(counts.values())
    return AdminTourList(items=items, counts=counts)


@router.get("/{tour_id}", response_model=AdminTour)
def get_tour(tour_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, tour_id)


@router.post("", response_model=AdminTour, status_code=status.HTTP_201_CREATED)
def create_tour(body: AdminTourCreate, db: Session = Depends(get_db)):
    assert_publishable(body.price_ghs, body.status, body.publish_at)
    tour = models.Tour(**{f: getattr(body, f) for f in NON_LOCATION_FIELDS}, is_active=body.status != "draft")
    # Every admin-created tour is popular: the public country pages list only popular tours.
    # It can still be turned off afterwards with PATCH.
    tour.is_popular = True
    db.add(tour)
    db.flush()
    _replace_locations(db, tour, body.location_ids)
    db.commit()
    db.refresh(tour)
    return tour


@router.patch("/{tour_id}", response_model=AdminTour)
def update_tour(tour_id: int, body: AdminTourUpdate, db: Session = Depends(get_db)):
    tour = _get_or_404(db, tour_id)
    changes = body.model_dump(exclude_unset=True)
    location_ids = changes.pop("location_ids", None)
    if changes.get("highlights", ...) is None:
        changes["highlights"] = []
    for field in ("name", "country", "status"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    for field, value in changes.items():
        setattr(tour, field, value)
    tour.is_active = tour.status != "draft"  # legacy field, kept in step with status
    # Only re-check publish rules when they're being changed, so existing
    # unpriced published tours can still be edited.
    if {"status", "price_ghs", "publish_at"} & changes.keys():
        assert_publishable(tour.price_ghs, tour.status, tour.publish_at)
    if location_ids is not None:
        _replace_locations(db, tour, location_ids)
    db.commit()
    db.refresh(tour)
    return tour


@router.delete("/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tour(tour_id: int, db: Session = Depends(get_db)):
    tour = _get_or_404(db, tour_id)
    booked = db.scalar(
        select(func.count()).select_from(models.BookingTour).where(models.BookingTour.tour_id == tour.id)
    ) or db.scalar(
        select(func.count()).select_from(models.BookingLocation).where(models.BookingLocation.tour_id == tour.id)
    )
    if booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This tour has bookings and can't be deleted. Set it to draft to hide it instead.",
        )
    db.execute(delete(models.TourLocation).where(models.TourLocation.tour_id == tour.id))
    db.execute(delete(models.ExtraPrice).where(models.ExtraPrice.tour_id == tour.id))
    db.execute(delete(analytics.TourPopularity).where(analytics.TourPopularity.tour_id == tour.id))
    for table in (analytics.MonthlyBookingStats, analytics.CustomerDemographics):
        db.execute(update(table).where(table.most_popular_tour_id == tour.id).values(most_popular_tour_id=None))
    db.delete(tour)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{tour_id}/extras/{extra_id}", response_model=AdminTour)
def attach_tour_extra(tour_id: int, extra_id: int, body: AttachExtraRequest, db: Session = Depends(get_db)):
    tour = _get_or_404(db, tour_id)
    attach_extra(db, get_extra_or_404(db, extra_id), body, tour_id=tour.id)
    db.refresh(tour)
    return tour


@router.delete("/{tour_id}/extras/{extra_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_tour_extra(tour_id: int, extra_id: int, db: Session = Depends(get_db)):
    tour = _get_or_404(db, tour_id)
    detach_extra(db, extra_id, tour_id=tour.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
