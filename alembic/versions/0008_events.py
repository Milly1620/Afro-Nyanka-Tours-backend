"""Events, event locations, and event foreign keys

Revision ID: 0008_events
Revises: 0007_booking_extras
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_events"
down_revision: Union[str, None] = "0007_booking_extras"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("region", sa.String()),
        sa.Column("destination", sa.String()),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("duration_days", sa.Integer()),
        sa.Column("price_ghs", sa.Integer()),
        sa.Column("capacity", sa.Integer()),
        sa.Column("highlights", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("main_image_url", sa.String()),
        sa.Column("gallery_images", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("publish_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('draft', 'published', 'scheduled')", name="ck_events_status"),
        sa.CheckConstraint("end_date >= start_date", name="ck_events_dates"),
    )
    op.create_index("ix_events_start_date", "events", ["start_date"])
    op.create_table(
        "event_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("order", sa.Integer()),
    )
    op.create_index("ix_event_locations_event_id", "event_locations", ["event_id"])

    op.add_column("bookings", sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id")))
    op.create_index("ix_bookings_event_id", "bookings", ["event_id"])
    op.create_foreign_key("extra_prices_event_id_fkey", "extra_prices", "events", ["event_id"], ["id"])
    op.create_foreign_key("booking_extras_event_id_fkey", "booking_extras", "events", ["event_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("booking_extras_event_id_fkey", "booking_extras", type_="foreignkey")
    op.drop_constraint("extra_prices_event_id_fkey", "extra_prices", type_="foreignkey")
    op.drop_index("ix_bookings_event_id", "bookings")
    op.drop_column("bookings", "event_id")
    op.drop_table("event_locations")
    op.drop_table("events")
