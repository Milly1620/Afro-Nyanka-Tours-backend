from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.database import Base


class Tour(Base):
    __tablename__ = "tours"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    country = Column(String, nullable=False)
    region = Column(String)
    # price_per_person = Column(Float, nullable=False)
    # max_participants = Column(Integer, default=20)
    # duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tour_locations = relationship("TourLocation", back_populates="tour")
    bookings = relationship("Booking", back_populates="tour")


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

    id = Column(Integer, primary_key=True, index=True)
    tour_id = Column(Integer, ForeignKey("tours.id"), nullable=False)
    
    # Customer information
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_age = Column(Integer)
    customer_country = Column(String)
    
    # Booking details
    preferred_date = Column(DateTime)
    additional_services = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tour = relationship("Tour", back_populates="bookings")
