from sqlalchemy.orm import Session
from sqlalchemy import func, extract, desc, and_, case
from src.models import models
from src.models.analytics import (
    MonthlyBookingStats, LocationPopularity, TourPopularity, 
    CustomerDemographics, BookingAnalytics
)
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta, timezone
from collections import defaultdict
import json
import calendar


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get high-level overview metrics for dashboard"""
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # Basic counts
        total_bookings = self.db.query(models.Booking).count()
        total_customers = self.db.query(models.Booking.customer_email).distinct().count()
        total_tours = self.db.query(models.Tour).filter(models.Tour.is_active == True).count()
        total_locations = self.db.query(models.Location).count()
        
        # This month's bookings
        this_month_bookings = self.db.query(models.Booking).filter(
            extract('month', models.Booking.created_at) == current_month,
            extract('year', models.Booking.created_at) == current_year
        ).count()
        
        # Last month's bookings for comparison
        last_month = current_month - 1 if current_month > 1 else 12
        last_month_year = current_year if current_month > 1 else current_year - 1
        
        last_month_bookings = self.db.query(models.Booking).filter(
            extract('month', models.Booking.created_at) == last_month,
            extract('year', models.Booking.created_at) == last_month_year
        ).count()
        
        # Calculate growth
        booking_growth = 0
        if last_month_bookings > 0:
            booking_growth = ((this_month_bookings - last_month_bookings) / last_month_bookings) * 100
        
        # Recent bookings (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        recent_bookings = self.db.query(models.Booking).filter(
            models.Booking.created_at >= thirty_days_ago
        ).count()
        
        return {
            "overview": {
                "total_bookings": total_bookings,
                "total_customers": total_customers,
                "total_tours": total_tours,
                "total_locations": total_locations,
                "this_month_bookings": this_month_bookings,
                "booking_growth_percentage": round(booking_growth, 2),
                "recent_bookings_30_days": recent_bookings
            },
            "last_updated": now.isoformat()
        }

    def get_monthly_booking_trends(self, months: int = 12) -> Dict[str, Any]:
        """Get booking trends over the last N months"""
        now = datetime.now()
        start_date = now - timedelta(days=months * 30)
        
        # Query monthly booking data
        monthly_data = self.db.query(
            extract('year', models.Booking.created_at).label('year'),
            extract('month', models.Booking.created_at).label('month'),
            func.count(models.Booking.id).label('bookings'),
            func.count(func.distinct(models.Booking.customer_email)).label('unique_customers')
        ).filter(
            models.Booking.created_at >= start_date
        ).group_by(
            extract('year', models.Booking.created_at),
            extract('month', models.Booking.created_at)
        ).order_by('year', 'month').all()
        
        # Format data for charts
        trends = []
        for row in monthly_data:
            month_name = calendar.month_name[int(row.month)]
            trends.append({
                "year": int(row.year),
                "month": int(row.month),
                "month_name": month_name,
                "period": f"{month_name} {int(row.year)}",
                "bookings": row.bookings,
                "unique_customers": row.unique_customers
            })
        
        return {
            "trends": trends,
            "total_periods": len(trends)
        }

    def get_popular_locations(self, limit: int = 10) -> Dict[str, Any]:
        """Get most popular locations by booking count"""
        popular_locations = self.db.query(
            models.Location.id,
            models.Location.name,
            models.Location.country,
            models.Location.region,
            func.count(models.BookingLocation.id).label('booking_count')
        ).join(
            models.BookingLocation
        ).group_by(
            models.Location.id,
            models.Location.name,
            models.Location.country,
            models.Location.region
        ).order_by(
            desc('booking_count')
        ).limit(limit).all()
        
        locations = []
        for row in popular_locations:
            locations.append({
                "id": row.id,
                "name": row.name,
                "country": row.country,
                "region": row.region,
                "booking_count": row.booking_count
            })
        
        return {
            "popular_locations": locations,
            "total_analyzed": len(locations)
        }

    def get_popular_tours(self, limit: int = 10) -> Dict[str, Any]:
        """Get most popular tours by booking count"""
        popular_tours = self.db.query(
            models.Tour.id,
            models.Tour.name,
            models.Tour.country,
            models.Tour.region,
            func.count(models.BookingTour.id).label('booking_count'),
            func.count(models.BookingLocation.id).label('total_locations_booked'),
            func.avg(
                func.count(models.BookingLocation.id)
            ).over(partition_by=models.Tour.id).label('avg_locations_per_booking')
        ).join(
            models.BookingTour
        ).outerjoin(
            models.BookingLocation,
            and_(
                models.BookingLocation.booking_id == models.BookingTour.booking_id,
                models.BookingLocation.tour_id == models.Tour.id
            )
        ).group_by(
            models.Tour.id,
            models.Tour.name,
            models.Tour.country,
            models.Tour.region
        ).order_by(
            desc('booking_count')
        ).limit(limit).all()
        
        tours = []
        for row in popular_tours:
            tours.append({
                "id": row.id,
                "name": row.name,
                "country": row.country,
                "region": row.region,
                "booking_count": row.booking_count,
                "total_locations_booked": row.total_locations_booked or 0,
                "avg_locations_per_booking": round(float(row.avg_locations_per_booking or 0), 2)
            })
        
        return {
            "popular_tours": tours,
            "total_analyzed": len(tours)
        }

    def get_customer_demographics(self) -> Dict[str, Any]:
        """Get customer demographics and patterns"""
        # Country-wise customer distribution
        country_stats = self.db.query(
            models.Booking.customer_country,
            func.count(func.distinct(models.Booking.customer_email)).label('unique_customers'),
            func.count(models.Booking.id).label('total_bookings'),
            func.avg(models.Booking.customer_age).label('avg_age')
        ).filter(
            models.Booking.customer_country.isnot(None)
        ).group_by(
            models.Booking.customer_country
        ).order_by(
            desc('total_bookings')
        ).all()
        
        countries = []
        for row in country_stats:
            countries.append({
                "country": row.customer_country,
                "unique_customers": row.unique_customers,
                "total_bookings": row.total_bookings,
                "avg_age": round(float(row.avg_age or 0), 1),
                "bookings_per_customer": round(row.total_bookings / row.unique_customers, 2)
            })
        
        # Age distribution
        age_distribution = self.db.query(
            case(
                (models.Booking.customer_age < 25, "Under 25"),
                (models.Booking.customer_age < 35, "25-34"),
                (models.Booking.customer_age < 45, "35-44"),
                (models.Booking.customer_age < 55, "45-54"),
                (models.Booking.customer_age < 65, "55-64"),
                else_="65+"
            ).label('age_group'),
            func.count(models.Booking.id).label('booking_count')
        ).filter(
            models.Booking.customer_age.isnot(None)
        ).group_by('age_group').all()
        
        age_groups = []
        for row in age_distribution:
            age_groups.append({
                "age_group": row.age_group,
                "booking_count": row.booking_count
            })
        
        return {
            "country_distribution": countries,
            "age_distribution": age_groups,
            "total_countries": len(countries)
        }

    def get_seasonal_patterns(self) -> Dict[str, Any]:
        """Analyze seasonal booking patterns"""
        # Monthly patterns across all years
        monthly_patterns = self.db.query(
            extract('month', models.Booking.created_at).label('month'),
            func.count(models.Booking.id).label('booking_count'),
            func.avg(func.count(models.Booking.id)).over().label('avg_monthly_bookings')
        ).group_by(
            extract('month', models.Booking.created_at)
        ).order_by('month').all()
        
        months = []
        for row in monthly_patterns:
            month_name = calendar.month_name[int(row.month)]
            months.append({
                "month": int(row.month),
                "month_name": month_name,
                "booking_count": row.booking_count,
                "above_average": row.booking_count > row.avg_monthly_bookings
            })
        
        # Day of week patterns
        dow_patterns = self.db.query(
            extract('dow', models.Booking.created_at).label('day_of_week'),
            func.count(models.Booking.id).label('booking_count')
        ).group_by(
            extract('dow', models.Booking.created_at)
        ).order_by('day_of_week').all()
        
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        day_patterns = []
        for row in dow_patterns:
            day_patterns.append({
                "day_number": int(row.day_of_week),
                "day_name": days[int(row.day_of_week)],
                "booking_count": row.booking_count
            })
        
        return {
            "monthly_patterns": months,
            "day_of_week_patterns": day_patterns,
            "peak_month": max(months, key=lambda x: x["booking_count"])["month_name"] if months else None,
            "peak_day": max(day_patterns, key=lambda x: x["booking_count"])["day_name"] if day_patterns else None
        }

    def get_booking_complexity_analysis(self) -> Dict[str, Any]:
        """Analyze how complex bookings are (multi-tour, multi-location)"""
        # Tours per booking analysis
        tours_per_booking = self.db.query(
            models.Booking.id,
            func.count(models.BookingTour.id).label('tour_count')
        ).outerjoin(
            models.BookingTour
        ).group_by(
            models.Booking.id
        ).subquery()
        
        tour_complexity = self.db.query(
            tours_per_booking.c.tour_count,
            func.count().label('frequency')
        ).group_by(
            tours_per_booking.c.tour_count
        ).order_by(tours_per_booking.c.tour_count).all()
        
        # Locations per booking analysis
        locations_per_booking = self.db.query(
            models.Booking.id,
            func.count(models.BookingLocation.id).label('location_count')
        ).outerjoin(
            models.BookingLocation
        ).group_by(
            models.Booking.id
        ).subquery()
        
        location_complexity = self.db.query(
            locations_per_booking.c.location_count,
            func.count().label('frequency')
        ).group_by(
            locations_per_booking.c.location_count
        ).order_by(locations_per_booking.c.location_count).all()
        
        # Calculate averages directly from base tables
        total_bookings = self.db.query(models.Booking).count()
        total_tours_booked = self.db.query(models.BookingTour).count()
        total_locations_booked = self.db.query(models.BookingLocation).count()
        
        avg_tours = total_tours_booked / total_bookings if total_bookings > 0 else 0
        avg_locations = total_locations_booked / total_bookings if total_bookings > 0 else 0
        
        tour_dist = [{"tours": int(row.tour_count), "frequency": row.frequency} for row in tour_complexity]
        location_dist = [{"locations": int(row.location_count), "frequency": row.frequency} for row in location_complexity]
        
        return {
            "tour_distribution": tour_dist,
            "location_distribution": location_dist,
            "averages": {
                "avg_tours_per_booking": round(avg_tours, 2),
                "avg_locations_per_booking": round(avg_locations, 2)
            }
        }

    def get_time_based_insights(self) -> Dict[str, Any]:
        """Get insights about booking timing and patterns"""
        now = datetime.now()
        
        # Recent activity (last 7 days)
        week_ago = now - timedelta(days=7)
        recent_activity = self.db.query(
            func.date(models.Booking.created_at).label('booking_date'),
            func.count(models.Booking.id).label('bookings')
        ).filter(
            models.Booking.created_at >= week_ago
        ).group_by(
            func.date(models.Booking.created_at)
        ).order_by('booking_date').all()
        
        daily_activity = []
        for row in recent_activity:
            daily_activity.append({
                "date": row.booking_date.isoformat(),
                "bookings": row.bookings
            })
        
        # Booking lead time analysis (time between booking and preferred date)
        lead_times = self.db.query(
            models.Booking.created_at,
            models.Booking.preferred_date
        ).filter(
            models.Booking.preferred_date.isnot(None)
        ).all()
        
        lead_time_analysis = []
        for booking in lead_times:
            if booking.preferred_date and booking.created_at:
                lead_days = (booking.preferred_date.date() - booking.created_at.date()).days
                if lead_days >= 0:  # Only count future bookings
                    lead_time_analysis.append(lead_days)
        
        avg_lead_time = sum(lead_time_analysis) / len(lead_time_analysis) if lead_time_analysis else 0
        
        return {
            "recent_daily_activity": daily_activity,
            "lead_time_insights": {
                "average_lead_time_days": round(avg_lead_time, 1),
                "min_lead_time": min(lead_time_analysis) if lead_time_analysis else 0,
                "max_lead_time": max(lead_time_analysis) if lead_time_analysis else 0,
                "total_analyzed": len(lead_time_analysis)
            }
        }

    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """Get all analytics in one comprehensive report"""
        return {
            "dashboard_overview": self.get_dashboard_overview(),
            "booking_trends": self.get_monthly_booking_trends(),
            "popular_locations": self.get_popular_locations(),
            "popular_tours": self.get_popular_tours(),
            "customer_demographics": self.get_customer_demographics(),
            "seasonal_patterns": self.get_seasonal_patterns(),
            "booking_complexity": self.get_booking_complexity_analysis(),
            "time_insights": self.get_time_based_insights(),
            "generated_at": datetime.now().isoformat()
        }

    def cache_analytics(self, analytics_data: Dict[str, Any]) -> None:
        """Cache analytics data for faster retrieval"""
        try:
            from src.models.analytics import BookingAnalytics
            import json
            
            # Convert analytics data to JSON string
            analytics_json = json.dumps(analytics_data, default=str)
            
            # Store or update the comprehensive analytics cache
            cached_analytics = self.db.query(BookingAnalytics).filter(
                BookingAnalytics.metric_name == "comprehensive_analytics"
            ).first()
            
            if cached_analytics:
                # Update existing cache
                cached_analytics.metric_data = analytics_json
                cached_analytics.last_calculated = datetime.now(timezone.utc)
            else:
                # Create new cache entry
                cached_analytics = BookingAnalytics(
                    metric_name="comprehensive_analytics",
                    metric_value=len(analytics_data),  # Store number of metrics as value
                    metric_data=analytics_json,
                    last_calculated=datetime.now(timezone.utc)
                )
                self.db.add(cached_analytics)
            
            # Cache individual metrics for faster access
            for metric_name, metric_data in analytics_data.items():
                if metric_name != "generated_at":  # Skip timestamp
                    existing_metric = self.db.query(BookingAnalytics).filter(
                        BookingAnalytics.metric_name == f"metric_{metric_name}"
                    ).first()
                    
                    metric_json = json.dumps(metric_data, default=str)
                    metric_value = 0
                    
                    # Extract a numeric value for common metrics
                    if isinstance(metric_data, dict):
                        if "total_bookings" in metric_data:
                            metric_value = metric_data["total_bookings"]
                        elif "total_customers" in metric_data:
                            metric_value = metric_data["total_customers"]
                        elif isinstance(metric_data, list) and len(metric_data) > 0:
                            metric_value = len(metric_data)
                    
                    if existing_metric:
                        existing_metric.metric_value = metric_value
                        existing_metric.metric_data = metric_json
                        existing_metric.last_calculated = datetime.now(timezone.utc)
                    else:
                        new_metric = BookingAnalytics(
                            metric_name=f"metric_{metric_name}",
                            metric_value=metric_value,
                            metric_data=metric_json,
                            last_calculated=datetime.now(timezone.utc)
                        )
                        self.db.add(new_metric)
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            # Log error but don't fail the main operation
            print(f"Failed to cache analytics: {str(e)}")

    def get_cached_analytics(self, max_age_hours: int = 1) -> Optional[Dict[str, Any]]:
        """Get cached analytics if available and not too old"""
        try:
            from src.models.analytics import BookingAnalytics
            from datetime import datetime, timedelta, timezone
            import json
            
            # Calculate the cutoff time for cache validity (using timezone-aware datetime)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            # Query for the comprehensive analytics cache
            cached_analytics = self.db.query(BookingAnalytics).filter(
                BookingAnalytics.metric_name == "comprehensive_analytics",
                BookingAnalytics.last_calculated >= cutoff_time
            ).first()
            
            if cached_analytics and cached_analytics.metric_data:
                try:
                    # Parse the cached JSON data
                    analytics_data = json.loads(cached_analytics.metric_data)
                    
                    # Add cache metadata
                    analytics_data["cache_info"] = {
                        "cached_at": cached_analytics.last_calculated.isoformat(),
                        "cache_age_hours": (datetime.now(timezone.utc) - cached_analytics.last_calculated).total_seconds() / 3600,
                        "is_cached": True
                    }
                    
                    return analytics_data
                except json.JSONDecodeError:
                    # If JSON parsing fails, return None to force fresh calculation
                    return None
            
            return None
            
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Failed to retrieve cached analytics: {str(e)}")
            return None
