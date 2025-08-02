from sqlalchemy.orm import Session
from src.models import models
from src.schemas import schemas
from typing import List, Optional


def get_tours(db: Session, skip: int = 0, limit: int = 100) -> List[models.Tour]:
    return db.query(models.Tour).filter(models.Tour.is_active == True).offset(skip).limit(limit).all()


def get_tour(db: Session, tour_id: int) -> Optional[models.Tour]:
    return db.query(models.Tour).filter(models.Tour.id == tour_id, models.Tour.is_active == True).first()


def get_tours_by_country(db: Session, country: str) -> List[models.Tour]:
    return db.query(models.Tour).filter(
        models.Tour.country.ilike(f"%{country}%"),
        models.Tour.is_active == True
    ).all()


def create_tour(db: Session, tour: schemas.TourCreate) -> models.Tour:
    db_tour = models.Tour(
        name=tour.name,
        description=tour.description,
        country=tour.country,
        region=tour.region,
        is_active=tour.is_active
    )
    db.add(db_tour)
    db.commit()
    db.refresh(db_tour)
    
    # Add tour locations
    for location_id in tour.location_ids:
        tour_location = models.TourLocation(
            tour_id=db_tour.id,
            location_id=location_id
        )
        db.add(tour_location)
    
    db.commit()
    db.refresh(db_tour)
    return db_tour


def get_locations(db: Session) -> List[models.Location]:
    return db.query(models.Location).all()


def get_location(db: Session, location_id: int) -> Optional[models.Location]:
    return db.query(models.Location).filter(models.Location.id == location_id).first()


def create_location(db: Session, location: schemas.LocationCreate) -> models.Location:
    db_location = models.Location(**location.dict())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


def create_booking(db: Session, booking: schemas.BookingCreate) -> models.Booking:
    # Get tour to validate it exists
    tour = get_tour(db, booking.tour_id)
    if not tour:
        raise ValueError("Tour not found")
    
    db_booking = models.Booking(
        tour_id=booking.tour_id,
        customer_name=booking.customer_name,
        customer_email=booking.customer_email,
        customer_age=booking.customer_age,
        customer_country=booking.customer_country,
        preferred_date=booking.preferred_date,
        additional_services=booking.additional_services
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def get_booking(db: Session, booking_id: int) -> Optional[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()


def get_bookings(db: Session, skip: int = 0, limit: int = 100) -> List[models.Booking]:
    return db.query(models.Booking).offset(skip).limit(limit).all()
