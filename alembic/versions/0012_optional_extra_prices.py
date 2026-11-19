"""Extra prices optional: NULL means price on request

Revision ID: 0012_optional_extra_prices
Revises: 0011_event_duration_from_dates
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_optional_extra_prices"
down_revision: Union[str, None] = "0011_event_duration_from_dates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("extra_prices", "price_ghs", existing_type=sa.Integer(), nullable=True)
    op.alter_column("booking_extras", "price_ghs", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Fails if any price-on-request rows exist; price them first.
    op.alter_column("booking_extras", "price_ghs", existing_type=sa.Integer(), nullable=False)
    op.alter_column("extra_prices", "price_ghs", existing_type=sa.Integer(), nullable=False)
