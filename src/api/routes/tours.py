from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.database.database import get_db
from src.schemas import schemas
from src.crud import crud

router = APIRouter()


@router.get("/", response_model=List[schemas.Tour])
def get_tours(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all active tours"""
    tours = crud.get_tours(db, skip=skip, limit=limit)
    return tours


@router.get("/{tour_id}", response_model=schemas.Tour)
def get_tour(tour_id: int, db: Session = Depends(get_db)):
    """Get a specific tour by ID"""
    tour = crud.get_tour(db, tour_id=tour_id)
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")
    return tour


@router.get("/country/{country}", response_model=List[schemas.Tour])
def get_tours_by_country(country: str, db: Session = Depends(get_db)):
    """Get tours by country"""
    tours = crud.get_tours_by_country(db, country=country)
    return tours


@router.post("/", response_model=schemas.Tour)
def create_tour(tour: schemas.TourCreate, db: Session = Depends(get_db)):
    """Create a new tour (admin only)"""
    return crud.create_tour(db=db, tour=tour)


@router.get("/locations/", response_model=List[schemas.Location])
def get_locations(db: Session = Depends(get_db)):
    """Get all locations"""
    return crud.get_locations(db)


@router.post("/locations/", response_model=schemas.Location)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    """Create a new location (admin only)"""
    return crud.create_location(db=db, location=location)
