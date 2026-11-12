import hmac
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.core.config import settings
from src.database.database import get_db
from src.schemas.admin_schemas import SiteSettingsAdmin, SiteSettingsPublic, SiteSettingsUpdate
from src.services.cloudinary_service import cloudinary_service
from src.services.dashboard import get_dashboard_metrics
from src.services.email_service import email_service
from src.services.site_settings import get_site_settings

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])  # /api/admin/settings
public_router = APIRouter()  # /api/settings
reports_router = APIRouter()  # /api/admin/reports, authorised by X-Cron-Secret


@router.get("", response_model=SiteSettingsAdmin)
def read_settings(db: Session = Depends(get_db)):
    return get_site_settings(db)


@router.put("", response_model=SiteSettingsAdmin)
def update_settings(body: SiteSettingsUpdate, db: Session = Depends(get_db)):
    row = get_site_settings(db)
    changes = body.model_dump(exclude_unset=True)
    for field in ("company_name", "contact_email", "notify_new_inquiry", "notify_booking_confirmation", "notify_weekly_summary"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/logo", response_model=SiteSettingsAdmin)
def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not cloudinary_service.validate_image_file(file):
        raise HTTPException(status_code=400, detail="Invalid image file. Please upload a valid image")
    result = cloudinary_service.upload_image(
        file, folder="afro-nyanka-tours/brand", transformation={"width": 512, "crop": "limit", "quality": "auto"}
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to upload image to cloud storage")
    row = get_site_settings(db)
    row.logo_url = result["url"]
    db.commit()
    db.refresh(row)
    return row


@public_router.get("/public", response_model=SiteSettingsPublic)
def public_settings(db: Session = Depends(get_db)):
    return get_site_settings(db)


@reports_router.post("/weekly-summary")
def weekly_summary(x_cron_secret: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not settings.cron_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="CRON_SECRET is not configured")
    if not x_cron_secret or not hmac.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")
    if not get_site_settings(db).notify_weekly_summary:
        return {"sent": False}
    sent = bool(email_service.send_weekly_summary(settings.admin_email, get_dashboard_metrics(db)))
    if not sent:
        logger.error("Weekly summary email failed to send")
    return {"sent": sent}
