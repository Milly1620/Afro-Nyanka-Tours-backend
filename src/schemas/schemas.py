from pydantic import BaseModel, EmailStr
from typing import List, Optional
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


class BookingBase(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_age: Optional[int] = None
    customer_country: Optional[str] = None
    preferred_date: Optional[datetime] = None
    additional_services: Optional[str] = None


class BookingCreate(BookingBase):
    tour_id: int


class Booking(BookingBase):
    id: int
    tour_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tour: Tour

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    booking: Booking
    message: str
