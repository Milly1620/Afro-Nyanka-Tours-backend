from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.core.security import _now, create_access_token, hash_one_time_token, hash_password, verify_password
from src.database.database import get_db
from src.models.admin import AdminUser, PasswordToken
from src.schemas.admin_schemas import (
    AdminMe,
    ForgotPasswordRequest,
    LoginRequest,
    SetPasswordRequest,
    TokenResponse,
)
from src.services.admin_bootstrap import apply_new_password, issue_password_link, normalise_email
from src.services.email_service import email_service
from src.core.config import settings
from src.services.rate_limit import (
    email_rate_limiter,
    forgot_email_limiter,
    forgot_ip_limiter,
    known_login_ips,
    login_rate_limiter,
)

router = APIRouter()

# Verified against on unknown emails so response time doesn't reveal which emails are admins.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def client_ip(request: Request) -> str:
    """Client IP for rate limiting.

    With TRUST_PROXY_HEADERS (Render), the proxy appends the connecting IP to
    X-Forwarded-For, so only the rightmost entry is trustworthy; anything to its
    left is client-supplied. Without a proxy the header is entirely
    client-supplied, so it is ignored.
    """
    forwarded = request.headers.get("x-forwarded-for") if settings.trust_proxy_headers else None
    if forwarded:
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = normalise_email(body.email)
    ip = client_ip(request)
    ip_key = f"{email}|{ip}"
    login_rate_limiter.begin([ip_key])
    # The per-email cap stops guessing from rotating IPs; an IP this admin has
    # already logged in from is exempt, so an attacker can't lock the admin out.
    email_keys = [] if known_login_ips.contains(email, ip) else [email]
    email_rate_limiter.begin(email_keys)

    admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
    if admin is None or not admin.is_active or not admin.password_hash:
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    login_rate_limiter.reset(ip_key)
    email_rate_limiter.succeed(email_keys)
    known_login_ips.add(email, ip)
    admin.last_login_at = _now()
    db.commit()
    token, expires_in = create_access_token(admin.id, body.remember_me, admin.password_changed_at)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: ForgotPasswordRequest, request: Request, background_tasks: BackgroundTasks):
    forgot_ip_limiter.begin([client_ip(request)])
    email = normalise_email(body.email)
    # Counted for every email, known or not; over the cap we quietly skip so the
    # reply is identical either way. The lookup runs after the response, so its
    # timing doesn't reveal which emails are admins.
    if forgot_email_limiter.allow(email):
        background_tasks.add_task(_send_reset_link, request.app.state.session_factory, email)
    return {"message": "If that account exists, a link has been sent."}


def _send_reset_link(session_factory, email: str) -> None:
    db = session_factory()
    try:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == email, AdminUser.is_active.is_(True)))
        if admin is None:
            return
        link = issue_password_link(db, admin, "reset")
        email_service.send_password_link(admin.email, link, "reset")
    finally:
        db.close()


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
def set_password(body: SetPasswordRequest, db: Session = Depends(get_db)):
    now = _now()
    active_admins = select(AdminUser.id).where(AdminUser.is_active.is_(True))
    admin_id = db.execute(
        update(PasswordToken)
        .where(
            PasswordToken.token_hash == hash_one_time_token(body.token),
            PasswordToken.used_at.is_(None),
            PasswordToken.expires_at > now,
            PasswordToken.admin_id.in_(active_admins),
        )
        .values(used_at=now)
        .returning(PasswordToken.admin_id)
    ).scalar()
    if admin_id is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has expired")

    apply_new_password(db, admin_id, body.password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AdminMe)
def me(admin: AdminUser = Depends(require_admin)):
    return admin
