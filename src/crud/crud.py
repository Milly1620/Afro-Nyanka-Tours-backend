from sqlalchemy.orm import Session
from src.models import models
from src.schemas import schemas
from typing import List, Optional, Dict


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


def get_tour_locations(db: Session, tour_id: int) -> List[models.Location]:
    """Get all locations available for a specific tour"""
    return db.query(models.Location).join(
        models.TourLocation
    ).filter(
        models.TourLocation.tour_id == tour_id
    ).all()


def validate_tour_locations(db: Session, tour_selections: List[schemas.BookingTourCreate]) -> bool:
    """Validate that all selected locations belong to their respective tours"""
    for selection in tour_selections:
        tour = get_tour(db, selection.tour_id)
        if not tour:
            raise ValueError(f"Tour with ID {selection.tour_id} not found")
        
        # Get valid location IDs for this tour
        valid_location_ids = {
            tl.location_id for tl in tour.tour_locations
        }
        
        # Check if all selected locations are valid for this tour
        for location_id in selection.locations:
            if location_id not in valid_location_ids:
                location = get_location(db, location_id)
                location_name = location.name if location else f"ID {location_id}"
                raise ValueError(
                    f"Location '{location_name}' is not available for tour '{tour.name}'"
                )
    
    return True


def create_booking(db: Session, booking: schemas.BookingCreate) -> models.Booking:
    """Create a new booking with multiple tours and locations"""
    
    # Validate tour selections
    validate_tour_locations(db, booking.tour_selections)
    
    # Create the main booking
    db_booking = models.Booking(
        customer_name=booking.customer_name,
        customer_email=booking.customer_email,
        customer_age=booking.customer_age,
        customer_country=booking.customer_country,
        preferred_date=booking.preferred_date,
        additional_services=booking.additional_services
    )
    db.add(db_booking)
    db.flush()  # Get the booking ID
    
    # Add selected tours to booking
    for selection in booking.tour_selections:
        # Create booking-tour relationship
        booking_tour = models.BookingTour(
            booking_id=db_booking.id,
            tour_id=selection.tour_id,
            order=selection.order
        )
        db.add(booking_tour)
        
        # Add selected locations for this tour
        for i, location_id in enumerate(selection.locations, 1):
            booking_location = models.BookingLocation(
                booking_id=db_booking.id,
                location_id=location_id,
                tour_id=selection.tour_id,
                order=i
            )
            db.add(booking_location)
    
    db.commit()
    db.refresh(db_booking)
    return db_booking


def get_booking(db: Session, booking_id: int) -> Optional[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()


def get_bookings(db: Session, skip: int = 0, limit: int = 100) -> List[models.Booking]:
    return db.query(models.Booking).offset(skip).limit(limit).all()


def get_booking_summary(db: Session, booking: models.Booking) -> Dict:
    """Get a summary of the booking with tour and location details"""
    summary = {
        "total_tours": len(booking.booking_tours),
        "total_locations": len(booking.booking_locations),
        "tours_and_locations": []
    }
    
    # Group locations by tour
    tour_locations = {}
    for bl in booking.booking_locations:
        if bl.tour_id not in tour_locations:
            tour_locations[bl.tour_id] = []
        tour_locations[bl.tour_id].append({
            "location_id": bl.location_id,
            "location_name": bl.location.name,
            "order": bl.order
        })
    
    # Add tour details with their locations
    for bt in booking.booking_tours:
        tour_info = {
            "tour_id": bt.tour.id,
            "tour_name": bt.tour.name,
            "country": bt.tour.country,
            "region": bt.tour.region,
            "selected_locations": sorted(
                tour_locations.get(bt.tour_id, []),
                key=lambda x: x["order"]
            )
        }
        summary["tours_and_locations"].append(tour_info)
    
    return summary
