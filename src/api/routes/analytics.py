from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from src.database.database import get_db
from src.services.analytics_service import AnalyticsService
from src.schemas.analytics_schemas import (
    ComprehensiveAnalytics, AnalyticsOverviewResponse, BookingTrendsResponse,
    PopularLocationsResponse, PopularToursResponse, CustomerDemographicsResponse,
    SeasonalPatternsResponse, BookingComplexityResponse, TimeInsightsResponse,
    AnalyticsHealthResponse
)
from datetime import datetime, timedelta, timezone
import logging
import csv
import io

logger = logging.getLogger(__name__)
router = APIRouter()


def convert_to_csv(data: dict, metric: str) -> str:
    """Convert analytics data to CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    if metric == "trends":
        # Monthly booking trends data
        writer.writerow(["Month", "Year", "Bookings", "Growth Rate"])
        for trend in data.get("monthly_trends", []):
            writer.writerow([
                trend.get("month"),
                trend.get("year"),
                trend.get("booking_count", 0),
                f"{trend.get('growth_rate', 0):.2f}%"
            ])
    
    elif metric == "locations":
        # Popular locations data
        writer.writerow(["Location ID", "Location Name", "Country", "Region", "Booking Count", "Percentage"])
        for location in data.get("popular_locations", []):
            writer.writerow([
                location.get("location_id"),
                location.get("location_name"),
                location.get("country"),
                location.get("region"),
                location.get("booking_count", 0),
                f"{location.get('percentage', 0):.2f}%"
            ])
    
    elif metric == "tours":
        # Popular tours data
        writer.writerow(["Tour ID", "Tour Name", "Country", "Region", "Booking Count", "Percentage"])
        for tour in data.get("popular_tours", []):
            writer.writerow([
                tour.get("tour_id"),
                tour.get("tour_name"),
                tour.get("country"),
                tour.get("region"),
                tour.get("booking_count", 0),
                f"{tour.get('percentage', 0):.2f}%"
            ])
    
    elif metric == "demographics":
        # Customer demographics data
        writer.writerow(["Demographic Type", "Category", "Count", "Percentage"])
        
        # Age groups
        for age_group in data.get("age_groups", []):
            writer.writerow([
                "Age Group",
                age_group.get("age_range"),
                age_group.get("count", 0),
                f"{age_group.get('percentage', 0):.2f}%"
            ])
        
        # Countries
        for country in data.get("countries", []):
            writer.writerow([
                "Country",
                country.get("country"),
                country.get("count", 0),
                f"{country.get('percentage', 0):.2f}%"
            ])
    
    return output.getvalue()

@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(db: Session = Depends(get_db)):
    """Get high-level analytics overview for dashboard"""
    try:
        analytics_service = AnalyticsService(db)
        overview_data = analytics_service.get_dashboard_overview()
        return overview_data
    except Exception as e:
        logger.error(f"Error getting analytics overview: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics overview")


@router.get("/trends", response_model=BookingTrendsResponse)
def get_booking_trends(
    months: int = Query(default=12, ge=1, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db)
):
    """Get booking trends over specified months"""
    try:
        analytics_service = AnalyticsService(db)
        trends_data = analytics_service.get_monthly_booking_trends(months)
        return trends_data
    except Exception as e:
        logger.error(f"Error getting booking trends: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch booking trends")


@router.get("/locations/popular", response_model=PopularLocationsResponse)
def get_popular_locations(
    limit: int = Query(default=10, ge=5, le=50, description="Number of top locations to return"),
    db: Session = Depends(get_db)
):
    """Get most popular locations by booking count"""
    try:
        analytics_service = AnalyticsService(db)
        locations_data = analytics_service.get_popular_locations(limit)
        return locations_data
    except Exception as e:
        logger.error(f"Error getting popular locations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch popular locations")


@router.get("/tours/popular", response_model=PopularToursResponse)
def get_popular_tours(
    limit: int = Query(default=10, ge=5, le=50, description="Number of top tours to return"),
    db: Session = Depends(get_db)
):
    """Get most popular tours by booking count"""
    try:
        analytics_service = AnalyticsService(db)
        tours_data = analytics_service.get_popular_tours(limit)
        return tours_data
    except Exception as e:
        logger.error(f"Error getting popular tours: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch popular tours")


@router.get("/demographics", response_model=CustomerDemographicsResponse)
def get_customer_demographics(db: Session = Depends(get_db)):
    """Get customer demographics and patterns"""
    try:
        analytics_service = AnalyticsService(db)
        demographics_data = analytics_service.get_customer_demographics()
        return demographics_data
    except Exception as e:
        logger.error(f"Error getting customer demographics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch customer demographics")


@router.get("/patterns/seasonal", response_model=SeasonalPatternsResponse)
def get_seasonal_patterns(db: Session = Depends(get_db)):
    """Get seasonal booking patterns and trends"""
    try:
        analytics_service = AnalyticsService(db)
        patterns_data = analytics_service.get_seasonal_patterns()
        return patterns_data
    except Exception as e:
        logger.error(f"Error getting seasonal patterns: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch seasonal patterns")


@router.get("/complexity", response_model=BookingComplexityResponse)
def get_booking_complexity(db: Session = Depends(get_db)):
    """Analyze booking complexity (multi-tour, multi-location patterns)"""
    try:
        analytics_service = AnalyticsService(db)
        complexity_data = analytics_service.get_booking_complexity_analysis()
        return complexity_data
    except Exception as e:
        logger.error(f"Error getting booking complexity: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch booking complexity analysis")


@router.get("/insights/time", response_model=TimeInsightsResponse)
def get_time_insights(db: Session = Depends(get_db)):
    """Get time-based insights and booking patterns"""
    try:
        analytics_service = AnalyticsService(db)
        time_data = analytics_service.get_time_based_insights()
        return time_data
    except Exception as e:
        logger.error(f"Error getting time insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch time insights")


@router.get("/comprehensive", response_model=ComprehensiveAnalytics)
def get_comprehensive_analytics(
    use_cache: bool = Query(default=True, description="Use cached data if available"),
    max_cache_age: int = Query(default=1, ge=1, le=24, description="Maximum cache age in hours"),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics report with all metrics"""
    try:
        analytics_service = AnalyticsService(db)
        
        # Try to get cached data first if requested
        if use_cache:
            cached_data = analytics_service.get_cached_analytics(max_cache_age)
            if cached_data:
                logger.info("Returning cached analytics data")
                return cached_data
        
        # Generate fresh analytics
        logger.info("Generating fresh analytics data")
        analytics_data = analytics_service.get_comprehensive_analytics()
        
        # Cache the results for future use
        analytics_service.cache_analytics(analytics_data)
        
        return analytics_data
    except Exception as e:
        logger.error(f"Error getting comprehensive analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch comprehensive analytics")


@router.post("/refresh-cache")
def refresh_analytics_cache(db: Session = Depends(get_db)):
    """Manually refresh the analytics cache"""
    try:
        analytics_service = AnalyticsService(db)
        
        # Generate fresh analytics
        analytics_data = analytics_service.get_comprehensive_analytics()
        
        # Cache the results
        analytics_service.cache_analytics(analytics_data)
        
        return {
            "message": "Analytics cache refreshed successfully",
            "generated_at": analytics_data["generated_at"],
            "metrics_cached": len(analytics_data) - 1  # Subtract 1 for generated_at
        }
    except Exception as e:
        logger.error(f"Error refreshing analytics cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to refresh analytics cache")


@router.get("/health", response_model=AnalyticsHealthResponse)
def get_analytics_health(db: Session = Depends(get_db)):
    """Get analytics system health and data coverage info"""
    try:
        from src.models import models
        from src.models.analytics import BookingAnalytics
        
        # Basic stats about data coverage
        total_bookings = db.query(models.Booking).count()
        
        if total_bookings == 0:
            return AnalyticsHealthResponse(
                total_bookings_analyzed=0,
                data_coverage_days=0,
                oldest_booking=None,
                newest_booking=None,
                cache_status={
                    "cached": False,
                    "last_updated": None,
                    "age_hours": None
                }
            )
        
        # Get date range of bookings
        oldest_booking = db.query(models.Booking.created_at).order_by(models.Booking.created_at.asc()).first()
        newest_booking = db.query(models.Booking.created_at).order_by(models.Booking.created_at.desc()).first()
        
        data_coverage_days = 0
        if oldest_booking and newest_booking:
            data_coverage_days = (newest_booking[0] - oldest_booking[0]).days
        
        # Check cache status
        latest_cache = db.query(BookingAnalytics).order_by(BookingAnalytics.last_calculated.desc()).first()
        
        # Calculate age_hours with proper timezone handling
        age_hours = None
        if latest_cache:
            # Ensure both datetimes are timezone-aware for comparison
            cache_time = latest_cache.last_calculated
            if cache_time.tzinfo is None:
                # If cache_time is naive, assume it's UTC
                cache_time = cache_time.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - cache_time).total_seconds() / 3600
        
        cache_status = {
            "cached": latest_cache is not None,
            "last_updated": latest_cache.last_calculated.isoformat() if latest_cache else None,
            "age_hours": age_hours
        }
        
        return AnalyticsHealthResponse(
            total_bookings_analyzed=total_bookings,
            data_coverage_days=data_coverage_days,
            oldest_booking=oldest_booking[0].isoformat() if oldest_booking else None,
            newest_booking=newest_booking[0].isoformat() if newest_booking else None,
            cache_status=cache_status
        )
    except Exception as e:
        logger.error(f"Error getting analytics health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics health info")



@router.get("/export/csv")
def export_analytics_csv(
    metric: str = Query(description="Metric to export: trends, locations, tours, demographics"),
    db: Session = Depends(get_db)
):
    """Export analytics data as CSV"""
    try:
        analytics_service = AnalyticsService(db)
       
        if metric == "trends":
            data = analytics_service.get_monthly_booking_trends(12)
        elif metric == "locations":
            data = analytics_service.get_popular_locations(50)
        elif metric == "tours":
            data = analytics_service.get_popular_tours(50)
        elif metric == "demographics":
            data = analytics_service.get_customer_demographics()
        else:
            raise HTTPException(status_code=400, detail="Invalid metric. Choose from: trends, locations, tours, demographics")
       
        # Convert data to CSV format
        csv_data = convert_to_csv(data, metric)
       
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analytics_{metric}_{timestamp}.csv"
       
        # Return CSV as a streaming response with proper iterator
        return StreamingResponse(
            io.BytesIO(csv_data.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error exporting analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export analytics data")