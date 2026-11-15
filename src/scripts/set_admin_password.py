"""Set an admin's password from a shell, without the emailed link.

    python -m src.scripts.set_admin_password owner@example.com

Prompts for the password twice (not echoed). The admin must already exist:
add the email to ADMIN_EMAILS and restart the app first. Setting the password
signs out the admin's existing sessions and voids any unused set/reset links.
"""
import getpass as getpass_module
import sys
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.admin import AdminUser
from src.services.admin_bootstrap import apply_new_password, normalise_email

MIN_LENGTH = 10
MAX_BYTES = 72  # bcrypt ignores anything past 72 bytes


def _password_problem(password: str) -> Optional[str]:
    if len(password) < MIN_LENGTH:
        return f"Password must be at least {MIN_LENGTH} characters."
    if len(password.encode("utf-8")) > MAX_BYTES:
        return f"Password must be at most {MAX_BYTES} bytes (accented letters count as 2)."
    return None


def main(
    argv: list[str],
    getpass: Callable[[str], str] = getpass_module.getpass,
    session_factory: Optional[Callable[[], Session]] = None,
) -> int:
    if len(argv) != 1:
        print("usage: python -m src.scripts.set_admin_password <email>", file=sys.stderr)
        return 2
    email = normalise_email(argv[0])

    if session_factory is None:
        from src.database.database import SessionLocal

        session_factory = SessionLocal
    db = session_factory()
    try:
        admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
        if admin is None:
            print(f"No admin account for {email}. Add it to ADMIN_EMAILS and restart the app first.", file=sys.stderr)
            return 1
        if not admin.is_active:
            print(f"{email} is deactivated. Add it back to ADMIN_EMAILS and restart the app first.", file=sys.stderr)
            return 1

        password = getpass("New password: ")
        problem = _password_problem(password)
        if problem:
            print(problem, file=sys.stderr)
            return 1
        if getpass("Repeat password: ") != password:
            print("Passwords don't match. Nothing changed.", file=sys.stderr)
            return 1

        apply_new_password(db, admin.id, password)
        db.commit()
    finally:
        db.close()
    print(f"Password set for {email}. Existing sessions were signed out.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
