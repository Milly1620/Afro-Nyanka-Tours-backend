"""Optional sharing and couple prices on events (NULL = not offered).

Revision ID: 0016_event_sharing_couple_prices
Revises: 0015_tidy_country_names
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_event_sharing_couple_prices"
down_revision: Union[str, None] = "0015_tidy_country_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("sharing_price_ghs", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("couple_price_ghs", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_events_sharing_price_nonnegative", "events", "sharing_price_ghs >= 0")
    op.create_check_constraint("ck_events_couple_price_nonnegative", "events", "couple_price_ghs >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_events_couple_price_nonnegative", "events", type_="check")
    op.drop_constraint("ck_events_sharing_price_nonnegative", "events", type_="check")
    op.drop_column("events", "couple_price_ghs")
    op.drop_column("events", "sharing_price_ghs")
