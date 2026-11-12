from fastapi import HTTPException, status as http_status
from sqlalchemy import and_, func, or_
from sqlalchemy.sql.elements import ColumnElement

PUBLISH_STATUSES = ("draft", "published", "scheduled")


def visible_filter(model) -> ColumnElement[bool]:
    """Rows the public may see: published, or scheduled with publish_at in the past."""
    return or_(
        model.status == "published",
        and_(model.status == "scheduled", model.publish_at <= func.now()),
    )


def assert_publishable(price_ghs, status: str, publish_at) -> None:
    """Published/scheduled items need a price; scheduled items need a publish time."""
    if status in ("published", "scheduled") and price_ghs is None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Set a price before publishing",
        )
    if status == "scheduled" and publish_at is None:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scheduled items need a publish_at time",
        )
