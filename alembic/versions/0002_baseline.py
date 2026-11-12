"""Baseline: create the schema that prod got from create_all

Revision d110fffbcf6a is empty; every existing table was created by
Base.metadata.create_all at app startup. This revision recreates that schema
idempotently so a fresh DB gets it and prod (where it exists) is a no-op apart
from drifted columns.

Revision ID: 0002_baseline
Revises: d110fffbcf6a
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_baseline"
down_revision: Union[str, None] = "d110fffbcf6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS tours (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        description TEXT,
        country VARCHAR NOT NULL,
        region VARCHAR,
        is_active BOOLEAN,
        main_image_url VARCHAR,
        gallery_images TEXT,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ
    )""",
    "ALTER TABLE tours ADD COLUMN IF NOT EXISTS is_popular BOOLEAN DEFAULT false",
    "CREATE INDEX IF NOT EXISTS ix_tours_id ON tours (id)",
    "CREATE INDEX IF NOT EXISTS ix_tours_name ON tours (name)",
    """CREATE TABLE IF NOT EXISTS locations (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        description TEXT,
        country VARCHAR NOT NULL,
        region VARCHAR,
        created_at TIMESTAMPTZ DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_locations_id ON locations (id)",
    "CREATE INDEX IF NOT EXISTS ix_locations_name ON locations (name)",
    """CREATE TABLE IF NOT EXISTS tour_locations (
        id SERIAL PRIMARY KEY,
        tour_id INTEGER NOT NULL REFERENCES tours (id),
        location_id INTEGER NOT NULL REFERENCES locations (id),
        "order" INTEGER
    )""",
    "CREATE INDEX IF NOT EXISTS ix_tour_locations_id ON tour_locations (id)",
    """CREATE TABLE IF NOT EXISTS bookings (
        id SERIAL PRIMARY KEY,
        customer_name VARCHAR NOT NULL,
        customer_email VARCHAR NOT NULL,
        customer_age INTEGER,
        customer_country VARCHAR,
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        number_of_people INTEGER NOT NULL,
        additional_services TEXT,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS ix_bookings_id ON bookings (id)",
    """CREATE TABLE IF NOT EXISTS booking_tours (
        id SERIAL PRIMARY KEY,
        booking_id INTEGER NOT NULL REFERENCES bookings (id),
        tour_id INTEGER NOT NULL REFERENCES tours (id),
        "order" INTEGER
    )""",
    "CREATE INDEX IF NOT EXISTS ix_booking_tours_id ON booking_tours (id)",
    """CREATE TABLE IF NOT EXISTS booking_locations (
        id SERIAL PRIMARY KEY,
        booking_id INTEGER NOT NULL REFERENCES bookings (id),
        location_id INTEGER NOT NULL REFERENCES locations (id),
        tour_id INTEGER NOT NULL REFERENCES tours (id),
        "order" INTEGER
    )""",
    "CREATE INDEX IF NOT EXISTS ix_booking_locations_id ON booking_locations (id)",
    """CREATE TABLE IF NOT EXISTS monthly_booking_stats (
        id SERIAL PRIMARY KEY,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        total_bookings INTEGER,
        total_customers INTEGER,
        total_tours_booked INTEGER,
        total_locations_booked INTEGER,
        most_popular_tour_id INTEGER REFERENCES tours (id),
        most_popular_location_id INTEGER REFERENCES locations (id),
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS ix_monthly_booking_stats_id ON monthly_booking_stats (id)",
    """CREATE TABLE IF NOT EXISTS location_popularity (
        id SERIAL PRIMARY KEY,
        location_id INTEGER NOT NULL REFERENCES locations (id),
        booking_count INTEGER,
        last_booked TIMESTAMPTZ,
        first_booked TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS ix_location_popularity_id ON location_popularity (id)",
    """CREATE TABLE IF NOT EXISTS tour_popularity (
        id SERIAL PRIMARY KEY,
        tour_id INTEGER NOT NULL REFERENCES tours (id),
        booking_count INTEGER,
        total_locations_selected INTEGER,
        avg_locations_per_booking DOUBLE PRECISION,
        last_booked TIMESTAMPTZ,
        first_booked TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS ix_tour_popularity_id ON tour_popularity (id)",
    """CREATE TABLE IF NOT EXISTS customer_demographics (
        id SERIAL PRIMARY KEY,
        country VARCHAR NOT NULL,
        customer_count INTEGER,
        total_bookings INTEGER,
        avg_age DOUBLE PRECISION,
        avg_tours_per_booking DOUBLE PRECISION,
        avg_locations_per_booking DOUBLE PRECISION,
        most_popular_tour_id INTEGER REFERENCES tours (id),
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ
    )""",
    "CREATE INDEX IF NOT EXISTS ix_customer_demographics_id ON customer_demographics (id)",
    "CREATE INDEX IF NOT EXISTS ix_customer_demographics_country ON customer_demographics (country)",
    """CREATE TABLE IF NOT EXISTS booking_analytics (
        id SERIAL PRIMARY KEY,
        metric_name VARCHAR NOT NULL,
        metric_value DOUBLE PRECISION NOT NULL,
        metric_data TEXT,
        last_calculated TIMESTAMPTZ DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_booking_analytics_id ON booking_analytics (id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_booking_analytics_metric_name ON booking_analytics (metric_name)",
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    # Baseline of pre-existing prod tables: never dropped by a downgrade.
    pass
