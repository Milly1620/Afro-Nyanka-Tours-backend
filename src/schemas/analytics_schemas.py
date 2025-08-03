from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, date


class DashboardOverview(BaseModel):
    total_bookings: int
    total_customers: int
    total_tours: int
    total_locations: int
    this_month_bookings: int
    booking_growth_percentage: float
    recent_bookings_30_days: int


class BookingTrend(BaseModel):
    year: int
    month: int
    month_name: str
    period: str
    bookings: int
    unique_customers: int


class BookingTrendsResponse(BaseModel):
    trends: List[BookingTrend]
    total_periods: int


class PopularLocation(BaseModel):
    id: int
    name: str
    country: str
    region: Optional[str]
    booking_count: int


class PopularLocationsResponse(BaseModel):
    popular_locations: List[PopularLocation]
    total_analyzed: int


class PopularTour(BaseModel):
    id: int
    name: str
    country: str
    region: Optional[str]
    booking_count: int
    total_locations_booked: int
    avg_locations_per_booking: float


class PopularToursResponse(BaseModel):
    popular_tours: List[PopularTour]
    total_analyzed: int


class CountryDemographic(BaseModel):
    country: str
    unique_customers: int
    total_bookings: int
    avg_age: float
    bookings_per_customer: float


class AgeDistribution(BaseModel):
    age_group: str
    booking_count: int


class CustomerDemographicsResponse(BaseModel):
    country_distribution: List[CountryDemographic]
    age_distribution: List[AgeDistribution]
    total_countries: int


class MonthlyPattern(BaseModel):
    month: int
    month_name: str
    booking_count: int
    above_average: bool


class DayPattern(BaseModel):
    day_number: int
    day_name: str
    booking_count: int


class SeasonalPatternsResponse(BaseModel):
    monthly_patterns: List[MonthlyPattern]
    day_of_week_patterns: List[DayPattern]
    peak_month: Optional[str]
    peak_day: Optional[str]


class ComplexityDistribution(BaseModel):
    tours: Optional[int] = None
    locations: Optional[int] = None
    frequency: int


class ComplexityAverages(BaseModel):
    avg_tours_per_booking: float
    avg_locations_per_booking: float


class BookingComplexityResponse(BaseModel):
    tour_distribution: List[ComplexityDistribution]
    location_distribution: List[ComplexityDistribution]
    averages: ComplexityAverages


class DailyActivity(BaseModel):
    date: str
    bookings: int


class LeadTimeInsights(BaseModel):
    average_lead_time_days: float
    min_lead_time: int
    max_lead_time: int
    total_analyzed: int


class TimeInsightsResponse(BaseModel):
    recent_daily_activity: List[DailyActivity]
    lead_time_insights: LeadTimeInsights


class ComprehensiveAnalytics(BaseModel):
    dashboard_overview: Dict[str, Any]
    booking_trends: Dict[str, Any]
    popular_locations: Dict[str, Any]
    popular_tours: Dict[str, Any]
    customer_demographics: Dict[str, Any]
    seasonal_patterns: Dict[str, Any]
    booking_complexity: Dict[str, Any]
    time_insights: Dict[str, Any]
    generated_at: str
    from_cache: Optional[bool] = False


# Individual response models for specific endpoints
class AnalyticsOverviewResponse(BaseModel):
    overview: DashboardOverview
    last_updated: str


class AnalyticsMetric(BaseModel):
    metric_name: str
    metric_value: float
    metric_data: Dict[str, Any]
    last_calculated: datetime


class CacheStatus(BaseModel):
    cached: bool
    last_updated: Optional[str]
    age_hours: Optional[float]


class AnalyticsHealthResponse(BaseModel):
    total_bookings_analyzed: int
    data_coverage_days: int
    oldest_booking: Optional[str]
    newest_booking: Optional[str]
    cache_status: CacheStatus
