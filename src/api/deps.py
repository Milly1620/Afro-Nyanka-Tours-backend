from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.core.security import decode_access_token
from src.database.database import get_db
from src.models.admin import AdminUser

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AdminUser:
    if creds is None:
        raise _unauthorized()
    try:
        admin_id = decode_access_token(creds.credentials)
    except JWTError:
        raise _unauthorized()
    admin = db.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        raise _unauthorized()
    return admin
