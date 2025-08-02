from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from src.database.database import get_db
from src.schemas import schemas
from src.crud import crud
from src.services.email_service import email_service

router = APIRouter()


@router.post("/", response_model=schemas.BookingResponse)
def create_booking(
    booking: schemas.BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new booking"""
    try:
        # Create the booking
        db_booking = crud.create_booking(db=db, booking=booking)
        
        # Send emails in background
        background_tasks.add_task(email_service.send_booking_confirmation, db_booking)
        background_tasks.add_task(email_service.send_admin_notification, db_booking)
        
        return schemas.BookingResponse(
            booking=db_booking,
            message="Booking created successfully! Confirmation emails have been sent."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create booking")


@router.get("/{booking_id}", response_model=schemas.Booking)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get a booking by ID"""
    booking = crud.get_booking(db, booking_id=booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/", response_model=List[schemas.Booking])
def get_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all bookings (admin only)"""
    return crud.get_bookings(db, skip=skip, limit=limit)
