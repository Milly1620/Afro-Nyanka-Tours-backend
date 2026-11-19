"""Events can span several countries (events.countries list)

Revision ID: 0013_event_countries
Revises: 0012_optional_extra_prices
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_event_countries"
down_revision: Union[str, None] = "0012_optional_extra_prices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("countries", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.execute("UPDATE events SET countries = json_build_array(country)")


def downgrade() -> None:
    op.drop_column("events", "countries")
