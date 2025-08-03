"""
Script to populate the database with predefined tour data from predefined_data.md
Run this after setting up the database
"""

from sqlalchemy.orm import Session
from src.database.database import SessionLocal, engine
from src.models.models import Base, Tour, Location, TourLocation

# Create all tables
Base.metadata.create_all(bind=engine)


def create_locations(db: Session):
    """Create predefined locations"""
    locations_data = [
        # Ghana - Accra
        {"name": "Independence Square", "country": "Ghana", "region": "Accra"},
        {"name": "National Museum", "country": "Ghana", "region": "Accra"},
        {"name": "Makola Market", "country": "Ghana", "region": "Accra"},
        {"name": "Jamestown", "country": "Ghana", "region": "Accra"},
        {"name": "Kwame Nkrumah Mausoleum", "country": "Ghana", "region": "Accra"},
        {"name": "W.E.B Dubois Center", "country": "Ghana", "region": "Accra"},
        {"name": "Accra Arts Center", "country": "Ghana", "region": "Accra"},
        {"name": "Chocolate Making Class", "country": "Ghana", "region": "Accra"},
        {"name": "Aburi Botanical Gardens", "country": "Ghana", "region": "Accra"},
        {"name": "Waterfall Tour", "country": "Ghana", "region": "Accra"},
        {"name": "Quad Biking", "country": "Ghana", "region": "Accra"},
        
        # Ghana - Cape Coast
        {"name": "Cape Coast Castle", "country": "Ghana", "region": "Cape Coast"},
        {"name": "Elmina Castle (Door of No Return)", "country": "Ghana", "region": "Cape Coast"},
        {"name": "Assin Manso Slave River", "country": "Ghana", "region": "Cape Coast"},
        {"name": "Kakum Canopy Walk", "country": "Ghana", "region": "Cape Coast"},
        {"name": "Naming Ceremony", "country": "Ghana", "region": "Cape Coast"},
        
        # Ghana - Kumasi
        {"name": "Manhyia Palace", "country": "Ghana", "region": "Kumasi"},
        {"name": "Adawomase", "country": "Ghana", "region": "Kumasi"},
        {"name": "Ntonso", "country": "Ghana", "region": "Kumasi"},
        
        # Ghana - Savannah
        {"name": "Mole National Park", "country": "Ghana", "region": "Savannah"},
        
        # Other countries
        {"name": "Voodoo Market", "country": "Togo", "region": "Lomé"},
        {"name": "Voodoo Market", "country": "Burkina Faso", "region": "Ouagadougou"}
        # {"name": "Safari Experience", "country": "Kenya", "region": "Nairobi"},
        # {"name": "Cultural Tour", "country": "Ethiopia", "region": "Addis Ababa"},
        # {"name": "Wine Tour", "country": "South Africa", "region": "Cape Town"},
        # {"name": "Mountain Adventure", "country": "Lesotho", "region": "Maseru"},
    ]
    
    created_locations = {}
    for location_data in locations_data:
        # Check if location already exists
        existing = db.query(Location).filter(
            Location.name == location_data["name"],
            Location.country == location_data["country"]
        ).first()
        
        if not existing:
            location = Location(**location_data)
            db.add(location)
            db.flush()  # Get the ID without committing
            created_locations[f"{location_data['name']}_{location_data['country']}"] = location.id
        else:
            created_locations[f"{location_data['name']}_{location_data['country']}"] = existing.id
    
    db.commit()
    return created_locations


def create_tours(db: Session, location_ids: dict):
    """Create predefined tours"""
    tours_data = [
        {
            "name": "Accra City Tours",
            "description": "Explore the vibrant capital of Ghana with visits to historical sites, museums, and cultural centers.",
            "country": "Ghana",
            "region": "Accra",
            "locations": [
                "Independence Square_Ghana",
                "National Museum_Ghana",
                "Makola Market_Ghana",
                "Jamestown_Ghana",
                "Kwame Nkrumah Mausoleum_Ghana",
                "W.E.B Dubois Center_Ghana",
                "Accra Arts Center_Ghana",
                "Chocolate Making Class_Ghana",
                "Aburi Botanical Gardens_Ghana",
                "Waterfall Tour_Ghana",
                "Quad Biking_Ghana"
            ]
        },
        {
            "name": "Cape Coast Tours",
            "description": "Experience the historical significance of Ghana's slave trade history and natural wonders.",
            "country": "Ghana",
            "region": "Cape Coast",
            "locations": [
                "Cape Coast Castle_Ghana",
                "Elmina Castle (Door of No Return)_Ghana",
                "Assin Manso Slave River_Ghana",
                "Kakum Canopy Walk_Ghana",
                "Naming Ceremony_Ghana"
            ]
        },
        {
            "name": "Kumasi City Tour",
            "description": "Discover the cultural heart of the Ashanti Kingdom.",
            "country": "Ghana",
            "region": "Kumasi",
            "locations": [
                "Manhyia Palace_Ghana",
                "Adawomase_Ghana",
                "Ntonso_Ghana"
            ]
        },
        {
            "name": "Savannah Region Tour",
            "description": "Wildlife safari in Ghana's premier national park.",
            "country": "Ghana",
            "region": "Savannah",
            "locations": [
                "Mole National Park_Ghana"
            ]
        },
        {
            "name": "Togo Voodoo Experience",
            "description": "Explore the mystical world of Voodoo culture.",
            "country": "Togo",
            "region": "Lomé",
            "locations": [
                "Voodoo Market_Togo"
            ]
        },
        {
            "name": "Burkina Faso Cultural Tour",
            "description": "Experience traditional West African culture and Voodoo practices.",
            "country": "Burkina Faso",
            "region": "Ouagadougou",
            "locations": [
                "Voodoo Market_Burkina Faso"
            ]
        }
        
    ]
    
    for tour_data in tours_data:
        # Check if tour already exists
        existing = db.query(Tour).filter(Tour.name == tour_data["name"]).first()
        if existing:
            continue
        
        # Create tour
        tour = Tour(
            name=tour_data["name"],
            description=tour_data["description"],
            country=tour_data["country"],
            region=tour_data["region"]
        )
        db.add(tour)
        db.flush()  # Get the ID
        
        # Add tour locations
        for i, location_key in enumerate(tour_data["locations"], 1):
            if location_key in location_ids:
                tour_location = TourLocation(
                    tour_id=tour.id,
                    location_id=location_ids[location_key],
                    order=i
                )
                db.add(tour_location)
    
    db.commit()


def main():
    """Main function to populate the database"""
    db = SessionLocal()
    try:
        print("Creating locations...")
        location_ids = create_locations(db)
        print(f"Created {len(location_ids)} locations")
        
        print("Creating tours...")
        create_tours(db, location_ids)
        print("Tours created successfully")
        
        print("Database populated successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
