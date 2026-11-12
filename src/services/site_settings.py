from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.models import models


def get_site_settings(db: Session) -> models.SiteSettings:
    """Return the single settings row, creating it with defaults if missing."""
    row = db.get(models.SiteSettings, 1)
    if row is None:
        db.execute(insert(models.SiteSettings).values(id=1).on_conflict_do_nothing(index_elements=["id"]))
        db.flush()
        row = db.get(models.SiteSettings, 1)
    return row


def company_context(row: models.SiteSettings) -> dict:
    """Company details for email templates."""
    return {
        "company_name": row.company_name,
        "contact_email": row.contact_email,
        "phone": row.phone,
        "location": row.location,
    }
