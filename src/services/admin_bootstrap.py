import logging
from datetime import timedelta
from typing import Callable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.security import _now, hash_password, new_one_time_token
from src.models.admin import AdminUser, PasswordToken

logger = logging.getLogger(__name__)

LINK_LIFETIME = timedelta(hours=24)


def apply_new_password(db: Session, admin_id: int, password: str) -> None:
    """Set an admin's password, sign out their sessions and void unused links. Caller commits."""
    now = _now()
    db.execute(
        update(AdminUser)
        .where(AdminUser.id == admin_id)
        .values(password_hash=hash_password(password), password_changed_at=now)
    )
    db.execute(
        update(PasswordToken)
        .where(PasswordToken.admin_id == admin_id, PasswordToken.used_at.is_(None))
        .values(used_at=now)
    )


def normalise_email(email: str) -> str:
    return email.strip().lower()


def parse_admin_emails(raw: str) -> list[str]:
    return [e for e in raw.split(",")]


def sync_admins(db: Session, emails: list[str]) -> list[str]:
    """Make admin_users match `emails`; return the emails newly created by this call.

    An empty list is treated as misconfiguration: nothing is deactivated.
    Concurrent callers are safe: ON CONFLICT DO NOTHING means only the
    inserting transaction gets the email back.
    """
    wanted: list[str] = []
    for email in emails:
        email = normalise_email(email)
        if email and email not in wanted:
            wanted.append(email)

    if not wanted:
        logger.warning("ADMIN_EMAILS is empty; leaving existing admin accounts unchanged")
        return []

    created: list[str] = []
    for email in wanted:
        inserted = db.execute(
            insert(AdminUser)
            .values(email=email, is_active=True)
            .on_conflict_do_nothing(index_elements=["email"])
            .returning(AdminUser.email)
        ).scalar()
        if inserted:
            created.append(inserted)

    db.execute(
        update(AdminUser)
        .where(AdminUser.email.in_(wanted), AdminUser.is_active.is_(False))
        .values(is_active=True)
    )
    db.execute(
        update(AdminUser)
        .where(AdminUser.email.not_in(wanted), AdminUser.is_active.is_(True))
        .values(is_active=False)
    )
    db.commit()
    return created


def issue_password_link(db: Session, admin: AdminUser, purpose: str) -> str:
    raw, hashed = new_one_time_token()
    db.add(
        PasswordToken(
            admin_id=admin.id,
            token_hash=hashed,
            purpose=purpose,
            expires_at=_now() + LINK_LIFETIME,
        )
    )
    db.commit()
    return f"{settings.frontend_url.rstrip('/')}/admin/set-password?token={raw}"


def run_startup_sync(session_factory: Callable[[], Session]) -> None:
    """Sync ADMIN_EMAILS and email set-password links to new admins. Never raises."""
    from src.services.email_service import email_service

    try:
        db = session_factory()
        try:
            created = sync_admins(db, parse_admin_emails(settings.admin_emails))
            for email in created:
                admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
                link = issue_password_link(db, admin, "set")
                if not email_service.send_password_link(email, link, "set"):
                    logger.error("Failed to send set-password email to %s", email)
        finally:
            db.close()
    except Exception:
        logger.exception("Admin bootstrap failed; startup continues")
