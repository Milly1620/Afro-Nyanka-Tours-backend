from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from src.schemas.schemas import Booking, PublicEvent, Tour
from src.services.countries import normalise_country, required_country

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
    is_popular: bool = True  # ignored: admin-created tours are always popular
    location_ids: List[int] = []

    _country = field_validator("country")(lambda cls, v: required_country(v))


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

    _country = field_validator("country")(lambda cls, v: v if v is None else required_country(v))


class AdminExtraPrice(BaseModel):
    extra_id: int
    name: str
    description: Optional[str] = None
    price_ghs: Optional[int] = None  # None = price on request
    is_active: bool


class AdminTour(Tour):
    status: str
    publish_at: Optional[datetime] = None
    is_popular: Optional[bool] = None
    extras: List[AdminExtraPrice] = Field(default=[], validation_alias="all_extras")


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


class ExtraCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    default_price_ghs: Optional[int] = Field(None, ge=0)


class ExtraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    default_price_ghs: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ExtraOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    default_price_ghs: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AttachExtraRequest(BaseModel):
    price_ghs: Optional[int] = Field(None, ge=0)


def clean_countries(countries: Optional[List[str]], country: Optional[str]) -> List[str]:
    """An event's countries: capitalised, without blanks or repeats, in the order given.

    `countries` wins; a single `country` string (older clients) may hold several, comma-separated.
    """
    raw = countries if countries is not None else (country or "").split(",")
    out: List[str] = []
    for name in raw:
        name = normalise_country(name)
        if name and name not in out:
            out.append(name)
    if not out:
        raise ValueError("An event needs at least one country")
    return out


class AdminEventCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    countries: Optional[List[str]] = None  # e.g. ["Ghana", "Togo", "Benin"]
    country: Optional[str] = None  # older clients: one country, or several comma-separated
    region: Optional[str] = None
    destination: Optional[str] = None
    start_date: date
    end_date: date
    duration_days: Optional[int] = Field(None, ge=1)
    price_ghs: Optional[int] = Field(None, ge=0)
    sharing_price_ghs: Optional[int] = Field(None, ge=0)
    couple_price_ghs: Optional[int] = Field(None, ge=0)
    capacity: Optional[int] = Field(None, ge=1)
    highlights: List[str] = []
    status: PublishStatus = "draft"
    publish_at: Optional[datetime] = None
    location_ids: List[int] = []

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        self.countries = clean_countries(self.countries, self.country)
        self.country = ", ".join(self.countries)
        return self


class AdminEventUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    countries: Optional[List[str]] = None
    country: Optional[str] = Field(None, min_length=1)
    region: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = Field(None, ge=1)
    price_ghs: Optional[int] = Field(None, ge=0)
    sharing_price_ghs: Optional[int] = Field(None, ge=0)
    couple_price_ghs: Optional[int] = Field(None, ge=0)
    capacity: Optional[int] = Field(None, ge=1)
    highlights: Optional[List[str]] = None
    status: Optional[PublishStatus] = None
    publish_at: Optional[datetime] = None
    location_ids: Optional[List[int]] = None


class AdminEvent(PublicEvent):
    status: str
    publish_at: Optional[datetime] = None
    seats_booked: int = 0
    extras: List[AdminExtraPrice] = Field(default=[], validation_alias="all_extras")
    created_at: datetime
    updated_at: Optional[datetime] = None


class AdminEventList(BaseModel):
    items: List[AdminEvent]
    counts: Dict[str, int]


class SiteSettingsPublic(BaseModel):
    company_name: str
    logo_url: Optional[str] = None
    contact_email: str
    phone: Optional[str] = None
    location: Optional[str] = None

    class Config:
        from_attributes = True


class SiteSettingsAdmin(SiteSettingsPublic):
    notify_new_inquiry: bool
    notify_booking_confirmation: bool
    notify_weekly_summary: bool
    updated_at: Optional[datetime] = None


class SiteSettingsUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1)
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    notify_new_inquiry: Optional[bool] = None
    notify_booking_confirmation: Optional[bool] = None
    notify_weekly_summary: Optional[bool] = None
