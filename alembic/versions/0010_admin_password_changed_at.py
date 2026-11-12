"""Admin password_changed_at (revokes tokens issued before a password change)

Revision ID: 0010_admin_password_changed_at
Revises: 0009_site_settings
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_admin_password_changed_at"
down_revision: Union[str, None] = "0009_site_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_users", sa.Column("password_changed_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("admin_users", "password_changed_at")
