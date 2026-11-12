"""Tour pricing fields and publish status

Revision ID: 0004_tour_pricing_status
Revises: 0003_admin_users
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_tour_pricing_status"
down_revision: Union[str, None] = "0003_admin_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tours", sa.Column("price_ghs", sa.Integer()))
    op.add_column("tours", sa.Column("duration_days", sa.Integer()))
    op.add_column("tours", sa.Column("capacity", sa.Integer()))
    op.add_column("tours", sa.Column("highlights", sa.JSON(), server_default=sa.text("'[]'"), nullable=True))
    op.add_column("tours", sa.Column("status", sa.String(16), server_default="draft", nullable=True))
    op.add_column("tours", sa.Column("publish_at", sa.DateTime(timezone=True)))

    # Existing active tours stay live; everything else becomes a draft.
    op.execute("UPDATE tours SET status = CASE WHEN is_active THEN 'published' ELSE 'draft' END")
    op.execute("UPDATE tours SET highlights = '[]' WHERE highlights IS NULL")
    op.alter_column("tours", "status", nullable=False)
    op.alter_column("tours", "highlights", nullable=False)
    op.create_check_constraint("ck_tours_status", "tours", "status IN ('draft', 'published', 'scheduled')")


def downgrade() -> None:
    op.drop_constraint("ck_tours_status", "tours", type_="check")
    for column in ("publish_at", "status", "highlights", "capacity", "duration_days", "price_ghs"):
        op.drop_column("tours", column)
