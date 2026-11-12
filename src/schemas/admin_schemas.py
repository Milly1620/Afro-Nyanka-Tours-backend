from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from src.schemas.schemas import Booking, Tour

PublishStatus = Literal["draft", "published", "scheduled"]


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: str


class SetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=10, max_length=72)


class AdminMe(BaseModel):
    id: int
    email: EmailStr


class AdminTourCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    country: str = Field(..., min_length=1)
    region: Optional[str] = None
    price_ghs: Optional[int] = Field(None, ge=0)
    duration_days: Optional[int] = Field(None, ge=1)
    capacity: Optional[int] = Field(None, ge=1)
    highlights: List[str] = []
    status: PublishStatus = "draft"
    publish_at: Optional[datetime] = None
    is_popular: bool = False
    location_ids: List[int] = []


class AdminTourUpdate(BaseModel):
    """Partial update: only fields present in the request are changed."""

    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    country: Optional[str] = Field(None, min_length=1)
    region: Optional[str] = None
    price_ghs: Optional[int] = Field(None, ge=0)
    duration_days: Optional[int] = Field(None, ge=1)
    capacity: Optional[int] = Field(None, ge=1)
    highlights: Optional[List[str]] = None
    status: Optional[PublishStatus] = None
    publish_at: Optional[datetime] = None
    is_popular: Optional[bool] = None
    location_ids: Optional[List[int]] = None


class AdminTour(Tour):
    status: str
    publish_at: Optional[datetime] = None
    is_popular: Optional[bool] = None


class AdminTourList(BaseModel):
    items: List[AdminTour]
    counts: Dict[str, int]


BookingStatus = Literal["pending", "confirmed", "paid", "cancelled"]


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class AdminBookingListItem(BaseModel):
    id: int
    reference: str
    customer_name: str
    customer_email: str
    tour_or_event_name: Optional[str] = None
    start_date: Optional[datetime] = None
    number_of_people: int
    amount_ghs: Optional[int] = None
    status: str
    created_at: datetime


class AdminBookingList(BaseModel):
    items: List[AdminBookingListItem]
    counts: Dict[str, int]


class AdminBookingDetail(BaseModel):
    booking: Booking
    summary: dict
