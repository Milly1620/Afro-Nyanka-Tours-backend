from sqlalchemy import Column, Integer, String, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database.database import Base


class MonthlyBookingStats(Base):
    """Track monthly booking statistics"""
    __tablename__ = "monthly_booking_stats"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    total_bookings = Column(Integer, default=0)
    total_customers = Column(Integer, default=0)
    total_tours_booked = Column(Integer, default=0)
    total_locations_booked = Column(Integer, default=0)
    most_popular_tour_id = Column(Integer, ForeignKey("tours.id"))
    most_popular_location_id = Column(Integer, ForeignKey("locations.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    most_popular_tour = relationship("Tour", foreign_keys=[most_popular_tour_id])
    most_popular_location = relationship("Location", foreign_keys=[most_popular_location_id])


class LocationPopularity(Base):
    """Track location booking popularity"""
    __tablename__ = "location_popularity"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    booking_count = Column(Integer, default=0)
    last_booked = Column(DateTime(timezone=True))
    first_booked = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    location = relationship("Location")


class TourPopularity(Base):
    """Track tour booking popularity"""
    __tablename__ = "tour_popularity"

    id = Column(Integer, primary_key=True, index=True)
    tour_id = Column(Integer, ForeignKey("tours.id"), nullable=False)
    booking_count = Column(Integer, default=0)
    total_locations_selected = Column(Integer, default=0)
    avg_locations_per_booking = Column(Float, default=0.0)
    last_booked = Column(DateTime(timezone=True))
    first_booked = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tour = relationship("Tour")


class CustomerDemographics(Base):
    """Track customer demographics and patterns"""
    __tablename__ = "customer_demographics"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, nullable=False, index=True)
    customer_count = Column(Integer, default=0)
    total_bookings = Column(Integer, default=0)
    avg_age = Column(Float)
    avg_tours_per_booking = Column(Float, default=0.0)
    avg_locations_per_booking = Column(Float, default=0.0)
    most_popular_tour_id = Column(Integer, ForeignKey("tours.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    most_popular_tour = relationship("Tour")


class BookingAnalytics(Base):
    """Store calculated analytics for quick retrieval"""
    __tablename__ = "booking_analytics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String, nullable=False, unique=True, index=True)
    metric_value = Column(Float, nullable=False)
    metric_data = Column(Text)  # JSON data for complex metrics
    last_calculated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships - None needed for this utility table
