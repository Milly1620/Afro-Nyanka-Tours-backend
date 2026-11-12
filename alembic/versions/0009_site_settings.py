"""Site settings singleton

Revision ID: 0009_site_settings
Revises: 0008_events
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_site_settings"
down_revision: Union[str, None] = "0008_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(), nullable=False, server_default="Afro Nyanka Tours"),
        sa.Column("logo_url", sa.String()),
        sa.Column("contact_email", sa.String(), nullable=False, server_default="info@afronyankatours.com"),
        sa.Column("phone", sa.String()),
        sa.Column("location", sa.String()),
        sa.Column("notify_new_inquiry", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_booking_confirmation", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_weekly_summary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_site_settings_singleton"),
    )
    op.execute("INSERT INTO site_settings (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("site_settings")
