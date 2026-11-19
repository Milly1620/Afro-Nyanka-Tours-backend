from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.database.database import get_db
from src.models import models
from src.schemas.admin_schemas import AttachExtraRequest, ExtraCreate, ExtraOut, ExtraUpdate

router = APIRouter(dependencies=[Depends(require_admin)])


def get_extra_or_404(db: Session, extra_id: int) -> models.Extra:
    extra = db.get(models.Extra, extra_id)
    if extra is None:
        raise HTTPException(status_code=404, detail="Extra not found")
    return extra


def attach_extra(db: Session, extra: models.Extra, body: AttachExtraRequest, *, tour_id=None, event_id=None) -> None:
    """Upsert the extra's price on one tour or event (defaults to the catalog price).

    With no price and no catalog price, the extra is "price on request".
    """
    price = body.price_ghs if body.price_ghs is not None else extra.default_price_ghs
    constraint = "uq_extra_prices_extra_tour" if tour_id is not None else "uq_extra_prices_extra_event"
    stmt = insert(models.ExtraPrice).values(extra_id=extra.id, tour_id=tour_id, event_id=event_id, price_ghs=price)
    db.execute(
        stmt.on_conflict_do_update(
            constraint=constraint,
            set_={"price_ghs": stmt.excluded.price_ghs},
        )
    )
    db.commit()


def detach_extra(db: Session, extra_id: int, *, tour_id=None, event_id=None) -> None:
    owner_col = models.ExtraPrice.tour_id if tour_id is not None else models.ExtraPrice.event_id
    db.execute(
        delete(models.ExtraPrice).where(
            models.ExtraPrice.extra_id == extra_id, owner_col == (tour_id if tour_id is not None else event_id)
        )
    )
    db.commit()


@router.get("", response_model=List[ExtraOut])
def list_extras(db: Session = Depends(get_db)):
    return db.scalars(select(models.Extra).order_by(models.Extra.is_active.desc(), models.Extra.name)).all()


@router.post("", response_model=ExtraOut, status_code=status.HTTP_201_CREATED)
def create_extra(body: ExtraCreate, db: Session = Depends(get_db)):
    extra = models.Extra(**body.model_dump())
    db.add(extra)
    db.commit()
    db.refresh(extra)
    return extra


@router.patch("/{extra_id}", response_model=ExtraOut)
def update_extra(extra_id: int, body: ExtraUpdate, db: Session = Depends(get_db)):
    extra = get_extra_or_404(db, extra_id)
    changes = body.model_dump(exclude_unset=True)
    for field in ("name", "is_active"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    for field, value in changes.items():
        setattr(extra, field, value)
    db.commit()
    db.refresh(extra)
    return extra
