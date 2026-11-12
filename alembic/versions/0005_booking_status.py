"""Booking status, amount and booking events

Revision ID: 0005_booking_status
Revises: 0004_tour_pricing_status
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_booking_status"
down_revision: Union[str, None] = "0004_tour_pricing_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing bookings become 'pending' with no amount (no prices existed then).
    op.add_column("bookings", sa.Column("status", sa.String(16), nullable=False, server_default="pending"))
    op.add_column("bookings", sa.Column("amount_ghs", sa.Integer()))
    op.create_check_constraint(
        "ck_bookings_status", "bookings", "status IN ('pending', 'confirmed', 'paid', 'cancelled')"
    )
    op.create_table(
        "booking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(16)),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('created', 'status_changed')", name="ck_booking_events_type"),
    )
    op.create_index("ix_booking_events_booking_id", "booking_events", ["booking_id"])
    op.create_index("ix_booking_events_created_at", "booking_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("booking_events")
    op.drop_constraint("ck_bookings_status", "bookings", type_="check")
    op.drop_column("bookings", "amount_ghs")
    op.drop_column("bookings", "status")
