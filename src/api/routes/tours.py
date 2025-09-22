from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from src.database.database import get_db
from src.schemas import schemas
from src.crud import crud
from src.services.cloudinary_service import cloudinary_service
import logging

logger = logging.getLogger(__name__)

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
def get_tours_by_country(country: str, is_popular: bool = True, db: Session = Depends(get_db)):
    """Get tours by country"""
    tours = crud.get_tours_by_country(db, country=country, is_popular=is_popular)
    return tours


@router.get("/tours/countries", response_model=schemas.CountriesResponse)
def get_countries_with_tours(db: Session = Depends(get_db)):
    """Get all countries that have active tours"""
    countries = crud.get_countries_with_tours(db)
    return schemas.CountriesResponse(countries=countries)


@router.post("/", response_model=schemas.Tour)
def create_tour(tour: schemas.TourCreate, db: Session = Depends(get_db)):
    """Create a new tour (admin only)"""
    return crud.create_tour(db=db, tour=tour)


@router.get("/locations/", response_model=List[schemas.Location])
def get_locations(db: Session = Depends(get_db)):
    """Get all locations"""
    return crud.get_locations(db)


@router.get("/locations/country/{country}", response_model=List[schemas.Location])
def get_locations_by_country(country: str, db: Session = Depends(get_db)):
    """Get all locations by country in random order"""
    locations = crud.get_locations_by_country(db, country=country)
    if not locations:
        raise HTTPException(status_code=404, detail=f"No locations found for country: {country}")
    return locations


@router.get("/{tour_id}/locations/", response_model=List[schemas.Location])
def get_tour_locations(tour_id: int, db: Session = Depends(get_db)):
    """Get all locations for a specific tour"""
    tour = crud.get_tour(db, tour_id=tour_id)
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")
    return crud.get_tour_locations(db, tour_id=tour_id)


@router.post("/locations/", response_model=schemas.Location)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    """Create a new location (admin only)"""
    return crud.create_location(db=db, location=location)

@router.patch("/tours/popular/{tour_id}", response_model=schemas.Tour)
def mark_tour_as_popular(tour_id: int, db: Session = Depends(get_db)):
    """Mark a tour as popular (admin only)"""
    tour = crud.get_tour(db, tour_id=tour_id)
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")
    tour.is_popular = True
    db.commit()
    db.refresh(tour)
    return tour


@router.post("/{tour_id}/upload-main-image", response_model=schemas.ImageUploadResponse)
async def upload_tour_main_image(
    tour_id: int,
    file: UploadFile = File(..., description="Main image for the tour"),
    db: Session = Depends(get_db)
):
    """
    Upload and set the main image for a tour
    
    This endpoint accepts an image file and uploads it to Cloudinary,
    then sets it as the main image for the specified tour.
    """
    # Verify tour exists
    tour = crud.get_tour(db, tour_id=tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    # Validate file
    if not cloudinary_service.validate_image_file(file):
        raise HTTPException(
            status_code=400, 
            detail="Invalid image file. Please upload a valid image (JPG, PNG, WebP, etc.)"
        )
    
    try:
        # Upload to Cloudinary
        upload_result = cloudinary_service.upload_image(
            file, 
            folder=f"afro-nyanka-tours/tour-{tour_id}/main"
        )
        
        if not upload_result:
            raise HTTPException(
                status_code=500, 
                detail="Failed to upload image to cloud storage"
            )
        
        # Update tour in database
        updated_tour = crud.update_tour_main_image(db, tour_id, upload_result["url"])
        
        if not updated_tour:
            # If database update fails, try to delete the uploaded image
            cloudinary_service.delete_image(upload_result["public_id"])
            raise HTTPException(
                status_code=500, 
                detail="Failed to update tour with new image"
            )
        
        logger.info(f"Main image uploaded for tour {tour_id}: {upload_result['url']}")
        
        return schemas.ImageUploadResponse(
            success=True,
            message="Main image uploaded successfully",
            image_url=upload_result["url"],
            public_id=upload_result["public_id"],
            image_details=upload_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading main image for tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during image upload"
        )


@router.post("/{tour_id}/upload-gallery-images", response_model=schemas.MultipleImageUploadResponse)
async def upload_tour_gallery_images(
    tour_id: int,
    files: List[UploadFile] = File(..., description="Gallery images for the tour"),
    db: Session = Depends(get_db)
):
    """
    Upload multiple images to a tour's gallery
    
    This endpoint accepts multiple image files and uploads them to Cloudinary,
    then adds them to the tour's gallery.
    """
    # Verify tour exists
    tour = crud.get_tour(db, tour_id=tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    if len(files) > 10:  # Limit to 10 images per upload
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10 images can be uploaded at once"
        )
    
    uploaded_images = []
    failed_uploads = []
    
    try:
        for file in files:
            # Validate each file
            if not cloudinary_service.validate_image_file(file):
                failed_uploads.append(f"{file.filename}: Invalid image file")
                continue
            
            # Upload to Cloudinary
            upload_result = cloudinary_service.upload_image(
                file, 
                folder=f"afro-nyanka-tours/tour-{tour_id}/gallery"
            )
            
            if upload_result:
                # Add to tour gallery
                crud.add_tour_gallery_image(db, tour_id, upload_result["url"])
                uploaded_images.append({
                    "filename": file.filename,
                    "url": upload_result["url"],
                    "public_id": upload_result["public_id"],
                    "details": upload_result
                })
                logger.info(f"Gallery image uploaded for tour {tour_id}: {upload_result['url']}")
            else:
                failed_uploads.append(f"{file.filename}: Upload failed")
        
        success_count = len(uploaded_images)
        total_count = len(files)
        
        return schemas.MultipleImageUploadResponse(
            success=success_count > 0,
            message=f"{success_count} out of {total_count} images uploaded successfully",
            uploaded_images=uploaded_images,
            failed_uploads=failed_uploads
        )
        
    except Exception as e:
        logger.error(f"Error uploading gallery images for tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during image upload"
        )


@router.delete("/{tour_id}/remove-gallery-image")
async def remove_tour_gallery_image(
    tour_id: int,
    image_url: str = Form(..., description="URL of the image to remove"),
    db: Session = Depends(get_db)
):
    """
    Remove an image from a tour's gallery
    
    This endpoint removes an image from the tour's gallery and optionally
    deletes it from Cloudinary storage.
    """
    # Verify tour exists
    tour = crud.get_tour(db, tour_id=tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    try:
        # Remove from database
        updated_tour = crud.remove_tour_gallery_image(db, tour_id, image_url)
        
        if updated_tour:
            # Extract public_id from URL to delete from Cloudinary
            if "cloudinary.com" in image_url:
                # Extract public_id from Cloudinary URL
                # URL format: https://res.cloudinary.com/cloud_name/image/upload/v1234567890/public_id.format
                parts = image_url.split("/")
                if len(parts) >= 7:
                    public_id_with_ext = "/".join(parts[7:])  # Everything after upload/version/
                    public_id = public_id_with_ext.rsplit(".", 1)[0]  # Remove file extension
                    
                    # Delete from Cloudinary
                    cloudinary_service.delete_image(public_id)
                    logger.info(f"Deleted image from Cloudinary: {public_id}")
            
            return {"success": True, "message": "Image removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Image not found in tour gallery")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing gallery image for tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while removing the image"
        )


@router.post("/{tour_id}/add-location", response_model=schemas.TourLocationResponse)
def add_location_to_tour(
    tour_id: int,
    request: schemas.AddLocationToTourRequest,
    db: Session = Depends(get_db)
):
    """
    Add a location to a tour
    
    This endpoint adds a location to the specified tour with an optional order.
    If no order is specified, the location will be added at the end.
    """
    try:
        # Add location to tour
        tour_location = crud.add_location_to_tour(
            db, tour_id, request.location_id, request.order
        )
        
        if not tour_location:
            raise HTTPException(
                status_code=404, 
                detail="Tour or location not found"
            )
        
        logger.info(f"Location {request.location_id} added to tour {tour_id}")
        
        return schemas.TourLocationResponse(
            success=True,
            message="Location added to tour successfully",
            tour_location=tour_location
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding location to tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding the location"
        )


@router.delete("/{tour_id}/remove-location", response_model=dict)
def remove_location_from_tour(
    tour_id: int,
    request: schemas.RemoveLocationFromTourRequest,
    db: Session = Depends(get_db)
):
    """
    Remove a location from a tour
    
    This endpoint removes the specified location from the tour.
    """
    try:
        # Remove location from tour
        success = crud.remove_location_from_tour(db, tour_id, request.location_id)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Tour-location relationship not found"
            )
        
        logger.info(f"Location {request.location_id} removed from tour {tour_id}")
        
        return {
            "success": True,
            "message": "Location removed from tour successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing location from tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while removing the location"
        )


@router.patch("/{tour_id}/update-location-order", response_model=schemas.TourLocationResponse)
def update_tour_location_order(
    tour_id: int,
    request: schemas.UpdateLocationOrderRequest,
    db: Session = Depends(get_db)
):
    """
    Update the order of a location within a tour
    
    This endpoint changes the order/position of a location within the tour.
    """
    try:
        # Update location order
        tour_location = crud.update_tour_location_order(
            db, tour_id, request.location_id, request.order
        )
        
        if not tour_location:
            raise HTTPException(
                status_code=404, 
                detail="Tour-location relationship not found"
            )
        
        logger.info(f"Location {request.location_id} order updated to {request.order} in tour {tour_id}")
        
        return schemas.TourLocationResponse(
            success=True,
            message="Location order updated successfully",
            tour_location=tour_location
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating location order in tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while updating the location order"
        )


@router.patch("/{tour_id}/reorder-locations", response_model=dict)
def reorder_tour_locations(
    tour_id: int,
    request: schemas.ReorderTourLocationsRequest,
    db: Session = Depends(get_db)
):
    """
    Reorder all locations in a tour
    
    This endpoint allows you to reorder multiple locations at once by
    providing a list of location IDs with their new order positions.
    """
    try:
        # Verify tour exists
        tour = crud.get_tour(db, tour_id)
        if not tour:
            raise HTTPException(status_code=404, detail="Tour not found")
        
        # Reorder locations
        success = crud.reorder_tour_locations(db, tour_id, request.location_orders)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to reorder locations"
            )
        
        logger.info(f"Locations reordered for tour {tour_id}")
        
        return {
            "success": True,
            "message": "Locations reordered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering locations for tour {tour_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while reordering locations"
        )


@router.get("/{tour_id}/location/{location_id}", response_model=schemas.TourLocation)
def get_tour_location_relationship(
    tour_id: int,
    location_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the relationship details between a tour and location
    
    This endpoint returns information about how a location is associated
    with a tour, including its order in the tour.
    """
    try:
        tour_location = crud.get_tour_location_relationship(db, tour_id, location_id)
        
        if not tour_location:
            raise HTTPException(
                status_code=404, 
                detail="Tour-location relationship not found"
            )
        
        return tour_location
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tour-location relationship: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )