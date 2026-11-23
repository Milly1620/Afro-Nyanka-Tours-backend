from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.services.countries import country_column_matches, normalise_country
from src.models import models
from src.schemas import schemas
from src.services.booking_status import booking_reference, record_created
from src.services.events import seats_booked, seats_left
from src.services.locations import replace_locations
from src.services.pricing import price_booking
from src.services.visibility import assert_publishable, visible_filter
from typing import List, Optional, Dict


def get_tours(db: Session, skip: int = 0, limit: int = 100) -> List[models.Tour]:
    return db.query(models.Tour).filter(visible_filter(models.Tour)).offset(skip).limit(limit).all()


def get_tour(db: Session, tour_id: int) -> Optional[models.Tour]:
    """Public lookup: only tours visible on the site."""
    return db.query(models.Tour).filter(models.Tour.id == tour_id, visible_filter(models.Tour)).first()


def get_tour_any(db: Session, tour_id: int) -> Optional[models.Tour]:
    """Admin lookup: any status, including drafts."""
    return db.get(models.Tour, tour_id)


def get_tours_by_country(db: Session, country: str, is_popular: bool = True) -> List[models.Tour]:
    if not is_popular:
        return db.query(models.Tour).filter(
            country_column_matches(models.Tour.country, country),
            visible_filter(models.Tour)
        ).all()
    return db.query(models.Tour).filter(
        country_column_matches(models.Tour.country, country),
        visible_filter(models.Tour),
        models.Tour.is_popular == True
    ).all()


def get_countries_with_tours(db: Session) -> List[str]:
    """Countries that have visible tours, one entry per country however it is spelled."""
    rows = db.query(models.Tour.country).filter(
        visible_filter(models.Tour)
    ).distinct().order_by(models.Tour.country).all()
    return list(dict.fromkeys(normalise_country(row[0]) for row in rows if row[0] and row[0].strip()))


def create_tour(db: Session, tour: schemas.TourCreate) -> models.Tour:
    """Legacy create: is_active=True publishes the tour (which needs a price), False keeps it a draft."""
    status = "published" if tour.is_active else "draft"
    assert_publishable(tour.price_ghs, status, None)
    db_tour = models.Tour(
        name=tour.name,
        description=tour.description,
        country=tour.country,
        region=tour.region,
        price_ghs=tour.price_ghs,
        duration_days=tour.duration_days,
        capacity=tour.capacity,
        highlights=tour.highlights,
        status=status,
        is_active=tour.is_active,
    )
    db.add(db_tour)
    db.flush()
    replace_locations(db, models.TourLocation, "tour_id", db_tour.id, tour.location_ids)
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


def update_tour_main_image(db: Session, tour_id: int, image_url: str) -> Optional[models.Tour]:
    """Update the main image URL for a tour"""
    tour = db.query(models.Tour).filter(models.Tour.id == tour_id).first()
    if tour:
        tour.main_image_url = image_url
        db.commit()
        db.refresh(tour)
    return tour


def add_tour_gallery_image(db: Session, tour_id: int, image_url: str) -> Optional[models.Tour]:
    """Add an image to the tour's gallery"""
    tour = db.query(models.Tour).filter(models.Tour.id == tour_id).first()
    if tour:
        import json
        # Parse existing gallery images or initialize empty list
        gallery_images = []
        if tour.gallery_images:
            try:
                gallery_images = json.loads(tour.gallery_images)
            except json.JSONDecodeError:
                gallery_images = []
        
        # Add new image if not already present
        if image_url not in gallery_images:
            gallery_images.append(image_url)
            tour.gallery_images = json.dumps(gallery_images)
            db.commit()
            db.refresh(tour)
    return tour


def update_tour_gallery_images(db: Session, tour_id: int, image_urls: List[str]) -> Optional[models.Tour]:
    """Replace all gallery images for a tour"""
    tour = db.query(models.Tour).filter(models.Tour.id == tour_id).first()
    if tour:
        import json
        tour.gallery_images = json.dumps(image_urls)
        db.commit()
        db.refresh(tour)
    return tour


def remove_tour_gallery_image(db: Session, tour_id: int, image_url: str) -> Optional[models.Tour]:
    """Remove a specific image from the tour's gallery"""
    tour = db.query(models.Tour).filter(models.Tour.id == tour_id).first()
    if tour and tour.gallery_images:
        import json
        try:
            gallery_images = json.loads(tour.gallery_images)
            if image_url in gallery_images:
                gallery_images.remove(image_url)
                tour.gallery_images = json.dumps(gallery_images)
                db.commit()
                db.refresh(tour)
        except json.JSONDecodeError:
            pass
    return tour


def add_location_to_tour(db: Session, tour_id: int, location_id: int, order: int = None) -> Optional[models.TourLocation]:
    """Add a location to a tour"""
    # Check if tour exists
    tour = get_tour_any(db, tour_id)
    if not tour:
        return None
    
    # Check if location exists
    location = get_location(db, location_id)
    if not location:
        return None
    
    # Check if relationship already exists
    existing = db.query(models.TourLocation).filter(
        models.TourLocation.tour_id == tour_id,
        models.TourLocation.location_id == location_id
    ).first()
    
    if existing:
        return existing  # Already exists, return existing relationship
    
    # Determine order if not provided
    if order is None:
        max_order = db.query(func.max(models.TourLocation.order)).filter(
            models.TourLocation.tour_id == tour_id
        ).scalar()
        order = (max_order or 0) + 1
    
    # Create new tour-location relationship
    tour_location = models.TourLocation(
        tour_id=tour_id,
        location_id=location_id,
        order=order
    )
    
    db.add(tour_location)
    db.commit()
    db.refresh(tour_location)
    return tour_location


def remove_location_from_tour(db: Session, tour_id: int, location_id: int) -> bool:
    """Remove a location from a tour"""
    # Find the relationship
    tour_location = db.query(models.TourLocation).filter(
        models.TourLocation.tour_id == tour_id,
        models.TourLocation.location_id == location_id
    ).first()
    
    if not tour_location:
        return False  # Relationship doesn't exist
    
    # Delete the relationship
    db.delete(tour_location)
    db.commit()
    return True


def update_tour_location_order(db: Session, tour_id: int, location_id: int, new_order: int) -> Optional[models.TourLocation]:
    """Update the order of a location within a tour"""
    tour_location = db.query(models.TourLocation).filter(
        models.TourLocation.tour_id == tour_id,
        models.TourLocation.location_id == location_id
    ).first()
    
    if not tour_location:
        return None
    
    tour_location.order = new_order
    db.commit()
    db.refresh(tour_location)
    return tour_location


def get_tour_location_relationship(db: Session, tour_id: int, location_id: int) -> Optional[models.TourLocation]:
    """Get the tour-location relationship"""
    return db.query(models.TourLocation).filter(
        models.TourLocation.tour_id == tour_id,
        models.TourLocation.location_id == location_id
    ).first()


def reorder_tour_locations(db: Session, tour_id: int, location_orders: List[Dict[str, int]]) -> bool:
    """
    Reorder locations in a tour
    
    Args:
        tour_id: ID of the tour
        location_orders: List of dicts with 'location_id' and 'order' keys
    
    Returns:
        True if successful, False otherwise
    """
    try:
        for item in location_orders:
            location_id = item.get('location_id')
            order = item.get('order')
            
            if location_id is None or order is None:
                continue
                
            tour_location = db.query(models.TourLocation).filter(
                models.TourLocation.tour_id == tour_id,
                models.TourLocation.location_id == location_id
            ).first()
            
            if tour_location:
                tour_location.order = order
        
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def get_tour_locations(db: Session, tour_id: int) -> List[models.Location]:
    """Get all locations available for a specific tour"""
    return db.query(models.Location).join(
        models.TourLocation
    ).filter(
        models.TourLocation.tour_id == tour_id
    ).all()


def get_locations_by_country(db: Session, country: str) -> List[models.Location]:
    """Get all locations by country in random order"""
    return db.query(models.Location).filter(
        country_column_matches(models.Location.country, country)
    ).order_by(func.random()).all()


def get_tour_locations_by_country(db: Session, country: str) -> List[models.Location]:
    """Get tour locations filtered by country in random order"""
    return db.query(models.Location).join(
        models.TourLocation
    ).filter(
        # models.TourLocation.tour_id == tour_id,
        country_column_matches(models.Location.country, country)
    ).order_by(func.random()).all()


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


def lock_bookable_event(db: Session, event_id: int, number_of_people: int) -> models.Event:
    """Lock the event row and check it can take this group.

    The row lock serialises concurrent bookings for the same event, so two
    requests can't both take the last seats. Held until the booking commits.
    """
    event = db.scalar(
        select(models.Event)
        .where(models.Event.id == event_id, visible_filter(models.Event))
        .with_for_update()
    )
    if event is None or event.start_date < date.today():
        raise HTTPException(status_code=400, detail=f"Event {event_id} is not available for booking")
    if event.capacity is not None:
        left = seats_left(event, seats_booked(db, [event.id])[event.id])
        if number_of_people > left:
            raise HTTPException(status_code=409, detail=f"Only {left} seats left")
    return event


def create_booking(db: Session, booking: schemas.BookingCreate) -> models.Booking:
    """Create a new booking with multiple tours and locations, priced server-side."""

    event = None
    tours: list = []
    start_date, end_date = booking.start_date, booking.end_date
    if booking.event_id is not None:
        event = lock_bookable_event(db, booking.event_id, booking.number_of_people)
        start_date = datetime.combine(event.start_date, datetime.min.time())
        end_date = datetime.combine(event.end_date, datetime.min.time())
    else:
        # Visible tours only; locations must belong to the tour
        validate_tour_locations(db, booking.tour_selections)
        tours = [get_tour(db, selection.tour_id) for selection in booking.tour_selections]
        for tour in tours:
            if tour.capacity is not None and booking.number_of_people > tour.capacity:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{tour.name}' takes groups of up to {tour.capacity} people",
                )
    priced = price_booking(db, booking, tours, event)

    # Create the main booking
    db_booking = models.Booking(
        customer_name=booking.customer_name,
        customer_email=booking.customer_email,
        customer_age=booking.customer_age,
        customer_country=booking.customer_country,
        start_date=start_date,
        end_date=end_date,
        number_of_people=booking.number_of_people,
        additional_services=booking.additional_services,
        amount_ghs=priced.amount_ghs,
        event_id=event.id if event is not None else None,
    )
    db.add(db_booking)
    db.flush()  # Get the booking ID
    record_created(db, db_booking)
    for snapshot in priced.extras:
        snapshot.booking_id = db_booking.id
        db.add(snapshot)

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
        "reference": booking_reference(booking.id),
        "status": booking.status,
        "amount_ghs": booking.amount_ghs,
        "extras": [{"name": e.name, "price_ghs": e.price_ghs} for e in booking.booking_extras],
        "event": (
            {
                "id": booking.event.id,
                "name": booking.event.name,
                "destination": booking.event.destination,
                "start_date": str(booking.event.start_date),
                "end_date": str(booking.event.end_date),
            }
            if booking.event is not None
            else None
        ),
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
