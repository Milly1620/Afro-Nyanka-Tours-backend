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
        # Benin - Cotonou
        {"name": "Cotonou City Tour", "country": "Benin", "region": "Cotonou"},
        {"name": "Cotonou Village", "country": "Benin", "region": "Cotonou"},
        {"name": "Voodoo Festival", "country": "Benin", "region": "Cotonou"},
        {"name": "Place de Martyrs", "country": "Benin", "region": "Cotonou"},
        
        # Cote d'Ivoire - Yamoussokro
        {"name": "The Basilica of Our Lady of Peace",
         "country": "Cote d'Ivoire", "region": "Yamoussokro"},
        {"name": "Palais Presidentiel",
         "country": "Cote d'Ivoire", "region": "Yamoussokro"},
        {"name": "Abokouamekro Game Reserve",
         "country": "Cote d'Ivoire", "region": "Yamoussokro"},
        
        # Cote d'Ivoire - Abidjan
        {"name": "Abidjan City Tour",
         "country": "Cote d'Ivoire", "region": "Abidjan"},
        {"name": "Banco National Park",
         "country": "Cote d'Ivoire", "region": "Abidjan"},
        {"name": "Domaine Bini Lagune",
         "country": "Cote d'Ivoire", "region": "Abidjan"},
        
        # Togo - Lome
        {"name": "Lome City Tour",
         "country": "Togo", "region": "Lome"},
        {"name": "Voodoo Market",
         "country": "Togo", "region": "Lome"},
        
        # Burkina Faso - Ouagadougou
        {"name": "Laongo Sculpture Symposium",
         "country": "Burkina Faso", "region": "Ouagadougou"},
        {"name": "Ouagadougou Markets",
         "country": "Burkina Faso", "region": "Ouagadougou"},
        {"name": "Reserve de Nazinga",
         "country": "Burkina Faso", "region": "Ouagadougou"},
        {"name": "Monument of National Heroes",
         "country": "Burkina Faso", "region": "Ouagadougou"},
        {"name": "Cathedral of Ouagadougou",
         "country": "Burkina Faso", "region": "Ouagadougou"}
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
            "name": "Benin Cotonou Experience",
            "description": ("Explore the vibrant city of Cotonou with its rich "
                           "cultural heritage, traditional villages, and "
                           "spiritual voodoo traditions."),
            "country": "Benin",
            "region": "Cotonou",
            "locations": [
                "Cotonou City Tour_Benin",
                "Cotonou Village_Benin",
                "Voodoo Festival_Benin",
                "Place de Martyrs_Benin"
            ]
        },
        {
            "name": "Yamoussokro Heritage Tour",
            "description": ("Discover the political and spiritual heart of "
                           "Cote d'Ivoire with visits to the world's largest "
                           "basilica and presidential palace."),
            "country": "Cote d'Ivoire",
            "region": "Yamoussokro",
            "locations": [
                "The Basilica of Our Lady of Peace_Cote d'Ivoire",
                "Palais Presidentiel_Cote d'Ivoire",
                "Abokouamekro Game Reserve_Cote d'Ivoire"
            ]
        },
        {
            "name": "Abidjan Urban Adventure",
            "description": ("Experience the economic capital of Cote d'Ivoire "
                           "with city tours, national parks, and lagoon "
                           "adventures."),
            "country": "Cote d'Ivoire",
            "region": "Abidjan",
            "locations": [
                "Abidjan City Tour_Cote d'Ivoire",
                "Banco National Park_Cote d'Ivoire",
                "Domaine Bini Lagune_Cote d'Ivoire"
            ]
        },
        {
            "name": "Togo Lome Discovery",
            "description": ("Immerse yourself in the coastal charm of Lome "
                           "with city exploration and mystical voodoo market "
                           "experiences."),
            "country": "Togo",
            "region": "Lome",
            "locations": [
                "Lome City Tour_Togo",
                "Voodoo Market_Togo"
            ]
        },
        {
            "name": "Ouagadougou Cultural Journey",
            "description": ("Explore the artistic and cultural treasures of "
                           "Burkina Faso's capital, from sculpture symposiums "
                           "to national monuments."),
            "country": "Burkina Faso",
            "region": "Ouagadougou",
            "locations": [
                "Laongo Sculpture Symposium_Burkina Faso",
                "Ouagadougou Markets_Burkina Faso",
                "Reserve de Nazinga_Burkina Faso",
                "Monument of National Heroes_Burkina Faso",
                "Cathedral of Ouagadougou_Burkina Faso"
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
