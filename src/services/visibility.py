from sqlalchemy import and_, func, or_
from sqlalchemy.sql.elements import ColumnElement

PUBLISH_STATUSES = ("draft", "published", "scheduled")


def visible_filter(model) -> ColumnElement[bool]:
    """Rows the public may see: published, or scheduled with publish_at in the past."""
    return or_(
        model.status == "published",
        and_(model.status == "scheduled", model.publish_at <= func.now()),
    )
