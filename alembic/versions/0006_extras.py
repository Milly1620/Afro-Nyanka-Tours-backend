"""Extras catalog and per-tour/event prices

Revision ID: 0006_extras
Revises: 0005_booking_status
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_extras"
down_revision: Union[str, None] = "0005_booking_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("default_price_ghs", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "extra_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extra_id", sa.Integer(), sa.ForeignKey("extras.id"), nullable=False),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id")),
        sa.Column("event_id", sa.Integer()),  # FK added in the events migration
        sa.Column("price_ghs", sa.Integer(), nullable=False),
        sa.CheckConstraint("num_nonnulls(tour_id, event_id) = 1", name="ck_extra_prices_one_owner"),
        sa.CheckConstraint("price_ghs >= 0", name="ck_extra_prices_price_nonnegative"),
        sa.UniqueConstraint("extra_id", "tour_id", name="uq_extra_prices_extra_tour"),
        sa.UniqueConstraint("extra_id", "event_id", name="uq_extra_prices_extra_event"),
    )
    op.create_index("ix_extra_prices_extra_id", "extra_prices", ["extra_id"])
    op.create_index("ix_extra_prices_tour_id", "extra_prices", ["tour_id"])
    op.create_index("ix_extra_prices_event_id", "extra_prices", ["event_id"])


def downgrade() -> None:
    op.drop_table("extra_prices")
    op.drop_table("extras")
