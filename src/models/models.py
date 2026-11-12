from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, CheckConstraint, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.database import Base


class Tour(Base):
    __tablename__ = "tours"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'scheduled')", name="ck_tours_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    country = Column(String, nullable=False)
    region = Column(String)
    is_active = Column(Boolean, default=True)
    main_image_url = Column(String)  
    gallery_images = Column(Text) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_popular = Column(Boolean, default=False)

    # Pricing and publishing (amounts are whole GHS)
    price_ghs = Column(Integer)
    duration_days = Column(Integer)
    capacity = Column(Integer)  # max group size per booking; NULL = no limit
    highlights = Column(JSON, nullable=False, server_default="[]", default=list)
    status = Column(String(16), nullable=False, server_default="draft", default="draft")
    publish_at = Column(DateTime(timezone=True))

    # Relationships
    tour_locations = relationship("TourLocation", back_populates="tour")
    booking_tours = relationship("BookingTour", back_populates="tour")
    extra_prices = relationship("ExtraPrice", back_populates="tour", lazy="selectin")

    @property
    def extras(self) -> list[dict]:
        """Active extras with this tour's price (what customers can pick)."""
        return [e for e in self.all_extras if e["is_active"]]

    @property
    def all_extras(self) -> list[dict]:
        return extra_price_rows(self.extra_prices)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    country = Column(String, nullable=False)
    region = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tour_locations = relationship("TourLocation", back_populates="location")
    booking_locations = relationship("BookingLocation", back_populates="location")


class TourLocation(Base):
    __tablename__ = "tour_locations"

    id = Column(Integer, primary_key=True, index=True)
    tour_id = Column(Integer, ForeignKey("tours.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    order = Column(Integer, default=1)  # Order of locations in the tour

    # Relationships
    tour = relationship("Tour", back_populates="tour_locations")
    location = relationship("Location", back_populates="tour_locations")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'paid', 'cancelled')", name="ck_bookings_status"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer information
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_age = Column(Integer)
    customer_country = Column(String)
    
    # Booking details
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    number_of_people = Column(Integer, nullable=False)
    additional_services = Column(Text)

    # Status workflow (set manually by the admin) and amount frozen at booking time
    status = Column(String(16), nullable=False, server_default="pending", default="pending")
    amount_ghs = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    booking_tours = relationship("BookingTour", back_populates="booking")
    booking_locations = relationship("BookingLocation", back_populates="booking")
    events = relationship("BookingEvent", back_populates="booking", order_by="BookingEvent.id")
    booking_extras = relationship("BookingExtra", back_populates="booking", order_by="BookingExtra.id")


class BookingTour(Base):
    __tablename__ = "booking_tours"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    tour_id = Column(Integer, ForeignKey("tours.id"), nullable=False)
    order = Column(Integer, default=1)  # Order of tours in the booking

    # Relationships
    booking = relationship("Booking", back_populates="booking_tours")
    tour = relationship("Tour", back_populates="booking_tours")


class BookingLocation(Base):
    __tablename__ = "booking_locations"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    tour_id = Column(Integer, ForeignKey("tours.id"), nullable=False)  # Which tour this location belongs to
    order = Column(Integer, default=1)  # Order of locations within the tour

    # Relationships
    booking = relationship("Booking", back_populates="booking_locations")
    location = relationship("Location", back_populates="booking_locations")
    tour = relationship("Tour")


class BookingEvent(Base):
    """History of a booking: creation and every status change (dashboard activity)."""

    __tablename__ = "booking_events"
    __table_args__ = (
        CheckConstraint("type IN ('created', 'status_changed')", name="ck_booking_events_type"),
    )

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False)
    from_status = Column(String(16))
    to_status = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    booking = relationship("Booking", back_populates="events")


def extra_price_rows(prices) -> list[dict]:
    rows = [
        {
            "extra_id": p.extra.id,
            "name": p.extra.name,
            "description": p.extra.description,
            "price_ghs": p.price_ghs,
            "is_active": p.extra.is_active,
        }
        for p in prices
    ]
    return sorted(rows, key=lambda r: (r["name"].lower(), r["extra_id"]))


class Extra(Base):
    """Shared catalog of paid add-ons; priced per tour/event via ExtraPrice."""

    __tablename__ = "extras"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    default_price_ghs = Column(Integer)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prices = relationship("ExtraPrice", back_populates="extra")


class ExtraPrice(Base):
    """An extra attached to exactly one tour or one event, at that offering's price."""

    __tablename__ = "extra_prices"
    __table_args__ = (
        CheckConstraint("num_nonnulls(tour_id, event_id) = 1", name="ck_extra_prices_one_owner"),
        CheckConstraint("price_ghs >= 0", name="ck_extra_prices_price_nonnegative"),
        UniqueConstraint("extra_id", "tour_id", name="uq_extra_prices_extra_tour"),
        UniqueConstraint("extra_id", "event_id", name="uq_extra_prices_extra_event"),
    )

    id = Column(Integer, primary_key=True)
    extra_id = Column(Integer, ForeignKey("extras.id"), nullable=False, index=True)
    tour_id = Column(Integer, ForeignKey("tours.id"), index=True)
    event_id = Column(Integer, index=True)  # FK to events.id added with the events table
    price_ghs = Column(Integer, nullable=False)

    extra = relationship("Extra", back_populates="prices", lazy="joined")
    tour = relationship("Tour", back_populates="extra_prices")


class BookingExtra(Base):
    """Snapshot of an extra chosen on a booking: name and price frozen at booking time."""

    __tablename__ = "booking_extras"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    extra_id = Column(Integer, ForeignKey("extras.id"), nullable=False)
    tour_id = Column(Integer, ForeignKey("tours.id"))
    event_id = Column(Integer)  # FK to events.id added with the events table
    name = Column(String, nullable=False)
    price_ghs = Column(Integer, nullable=False)

    booking = relationship("Booking", back_populates="booking_extras")
