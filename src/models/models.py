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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tour_locations = relationship("TourLocation", back_populates="tour")
    booking_tours = relationship("BookingTour", back_populates="tour")


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

    id = Column(Integer, primary_key=True, index=True)
    
    # Customer information
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_age = Column(Integer)
    customer_country = Column(String)
    
    # Booking details
    preferred_date = Column(DateTime)
    number_of_people = Column(Integer, nullable=False)
    additional_services = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    booking_tours = relationship("BookingTour", back_populates="booking")
    booking_locations = relationship("BookingLocation", back_populates="booking")


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
