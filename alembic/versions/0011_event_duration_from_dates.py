"""Fill event duration_days from the dates (both days counted)

Revision ID: 0011_event_duration_from_dates
Revises: 0010_admin_password_changed_at
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011_event_duration_from_dates"
down_revision: Union[str, None] = "0010_admin_password_changed_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # date - date is a whole number of days in Postgres
    op.execute("UPDATE events SET duration_days = end_date - start_date + 1")


def downgrade() -> None:
    pass  # the previous values were typed by hand and are not kept
