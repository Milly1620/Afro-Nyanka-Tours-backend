"""Mark every existing tour popular (admin-created tours now always are)

Revision ID: 0014_all_tours_popular
Revises: 0013_event_countries
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0014_all_tours_popular"
down_revision: Union[str, None] = "0013_event_countries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE tours SET is_popular = true WHERE is_popular IS NOT TRUE")


def downgrade() -> None:
    pass  # which tours were not popular before is not kept
