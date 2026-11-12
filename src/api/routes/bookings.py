from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from src.database.database import get_db
from src.api.deps import require_admin
from src.schemas import schemas
from src.crud import crud
from src.services.email_service import email_service
from src.services.site_settings import company_context, get_site_settings

router = APIRouter()


def booking_message(summary: dict) -> str:
    if summary.get("event"):
        return f"Booking {summary['reference']} received for {summary['event']['name']}."
    return (
        f"Booking {summary['reference']} received: {summary['total_tours']} tours with "
        f"{summary['total_locations']} locations."
    )


@router.post("/", response_model=schemas.BookingResponse)
def create_booking(
    booking: schemas.BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new multi-tour booking"""
    try:
        # Create the booking
        db_booking = crud.create_booking(db=db, booking=booking)
        
        # Get booking summary for emails
        booking_summary = crud.get_booking_summary(db, db_booking)
    
        # Send emails in background, as enabled in admin settings
        site = get_site_settings(db)
        if site.notify_booking_confirmation:
            background_tasks.add_task(
                email_service.send_booking_confirmation, db_booking, booking_summary, company_context(site)
            )
        if site.notify_new_inquiry:
            background_tasks.add_task(email_service.send_admin_notification, db_booking, booking_summary)
        
        return schemas.BookingResponse(
            booking=db_booking,
            message=booking_message(booking_summary),
            summary=booking_summary
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create booking: {str(e)}")


@router.get("/{booking_id}", response_model=schemas.Booking, dependencies=[Depends(require_admin)])
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    """Get a booking by ID"""
    booking = crud.get_booking(db, booking_id=booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/{booking_id}/summary", dependencies=[Depends(require_admin)])
def get_booking_summary(booking_id: int, db: Session = Depends(get_db)):
    """Get a detailed summary of a booking"""
    booking = crud.get_booking(db, booking_id=booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    summary = crud.get_booking_summary(db, booking)
    return {
        "booking_id": booking_id,
        "customer_name": booking.customer_name,
        "summary": summary
    }


@router.get("/", response_model=List[schemas.Booking], dependencies=[Depends(require_admin)])
def get_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all bookings (admin only)"""
    return crud.get_bookings(db, skip=skip, limit=limit)


@router.post("/test-email", dependencies=[Depends(require_admin)])
def test_email():
    """Test email configuration"""
    try:
        # Create a simple test email
        result = email_service.send_email(
            to_email=email_service.admin_email,
            subject="Test Email - Afro Nyanka Tours",
            html_content="""
            <html>
            <body>
                <h2>Email Test</h2>
                <p>This is a test email to verify email configuration is working.</p>
                <p>If you receive this email, the configuration is correct!</p>
            </body>
            </html>
            """
        )
        
        if result:
            return {"message": "Test email sent successfully!"}
        else:
            return {"message": "Failed to send test email. Check logs for details."}
    except Exception as e:
        return {"message": f"Error testing email: {str(e)}"}
