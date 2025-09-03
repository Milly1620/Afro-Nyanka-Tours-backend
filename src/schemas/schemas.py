from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class LocationBase(BaseModel):
    name: str
    description: Optional[str] = None
    country: str
    region: Optional[str] = None


class LocationCreate(LocationBase):
    pass


class Location(LocationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TourLocationBase(BaseModel):
    location_id: int
    order: int = 1


class TourLocationCreate(TourLocationBase):
    pass


class TourLocation(TourLocationBase):
    id: int
    location: Location

    class Config:
        from_attributes = True


class TourBase(BaseModel):
    name: str
    description: Optional[str] = None
    country: str
    region: Optional[str] = None
    is_active: bool = True


class TourCreate(TourBase):
    location_ids: List[int] = []


class Tour(TourBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tour_locations: List[TourLocation] = []

    class Config:
        from_attributes = True


class CountriesResponse(BaseModel):
    countries: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "countries": ["Ghana", "Nigeria", "South Africa", "Kenya"]
            }
        }


# New schemas for multi-tour/location booking
class BookingLocationCreate(BaseModel):
    location_id: int
    tour_id: int
    order: int = 1


class BookingLocation(BaseModel):
    id: int
    location_id: int
    tour_id: int
    order: int
    location: Location

    class Config:
        from_attributes = True


class BookingTourCreate(BaseModel):
    tour_id: int
    locations: List[int] = []
    order: int = 1


class BookingTour(BaseModel):
    id: int
    tour_id: int
    order: int
    tour: Tour

    class Config:
        from_attributes = True


class BookingBase(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_age: Optional[int] = None
    customer_country: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    additional_services: Optional[str] = None
    number_of_people: int = Field(default=1, description="Number of people in the booking")


class BookingCreate(BookingBase):
    tour_selections: List[BookingTourCreate]  # Multiple tours with selected locations
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "customer_age": 30,
                "customer_country": "USA",
                "start_date": "2024-06-15T00:00:00",
                "end_date": "2024-06-20T00:00:00",
                "additional_services": "Airport pickup required",
                "number_of_people": 3,
                "tour_selections": [
                    {
                        "tour_id": 1,
                        "locations": [1, 4, 5],  # Independence Square, Jamestown, Kwame Nkrumah Mausoleum
                        "order": 1
                    },
                    {
                        "tour_id": 2,
                        "locations": [13],  # Elmina Castle
                        "order": 2
                    }
                ]
            }
        }


class Booking(BookingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    booking_locations: List[BookingLocation] = []

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    booking: Booking
    message: str
    summary: Dict[str, Any] = {}  # Summary of selected tours and locations


class ContactForm(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    message: str = Field(..., min_length=10, max_length=2000, description="Message content")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "subject": "Inquiry about Ghana tour packages",
                "message": "Hello, I'm interested in learning more about your Ghana tour packages. Could you please provide more details about the pricing and availability for next month?"
            }
        }


class ContactResponse(BaseModel):
    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Your message has been sent successfully! We'll get back to you soon.",
                "success": True
            }
        }
