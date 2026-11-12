"""Booking extras snapshot

Revision ID: 0007_booking_extras
Revises: 0006_extras
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_booking_extras"
down_revision: Union[str, None] = "0006_extras"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_extras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extra_id", sa.Integer(), sa.ForeignKey("extras.id"), nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id")),
        sa.Column("event_id", sa.Integer()),  # FK added in the events migration
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price_ghs", sa.Integer(), nullable=False),
    )
    op.create_index("ix_booking_extras_booking_id", "booking_extras", ["booking_id"])


def downgrade() -> None:
    op.drop_table("booking_extras")
