"""Store every country under its main name (e.g. "Cote d'Ivoire" -> "Côte d'Ivoire")

Revision ID: 0015_tidy_country_names
Revises: 0014_all_tours_popular
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.services.countries import normalise_country

revision: str = "0015_tidy_country_names"
down_revision: Union[str, None] = "0014_all_tours_popular"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for table in ("tours", "locations"):
        for row_id, country in conn.execute(sa.text(f"SELECT id, country FROM {table}")).all():
            tidy = normalise_country(country or "")
            if tidy and tidy != country:
                conn.execute(sa.text(f"UPDATE {table} SET country = :c WHERE id = :id"), {"c": tidy, "id": row_id})

    for row_id, countries in conn.execute(sa.text("SELECT id, countries FROM events")).all():
        if isinstance(countries, str):
            countries = json.loads(countries)
        tidy = list(dict.fromkeys(c for c in (normalise_country(x) for x in countries or []) if c))
        if tidy and tidy != countries:
            conn.execute(
                sa.text("UPDATE events SET countries = CAST(:cs AS json), country = :c WHERE id = :id"),
                {"cs": json.dumps(tidy, ensure_ascii=False), "c": ", ".join(tidy), "id": row_id},
            )


def downgrade() -> None:
    pass  # the old spellings are not kept
