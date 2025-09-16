import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.utils import cloudinary_url
import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import UploadFile
import json
from src.core.config import settings

logger = logging.getLogger(__name__)


class CloudinaryService:
    def __init__(self):
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        print("Cloudinary configured with:", settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY is not None, settings.CLOUDINARY_API_SECRET is not None)
        # Validate configuration
        if not all([
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET
        ]):
            logger.warning("Cloudinary configuration incomplete. Image upload will not work.")

    def upload_image(
        self, 
        file: UploadFile, 
        folder: str = "afro-nyanka-tours",
        transformation: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, str]]:
        """
        Upload an image to Cloudinary
        
        Args:
            file: FastAPI UploadFile object
            folder: Cloudinary folder to store the image
            transformation: Optional transformation parameters
            
        Returns:
            Dictionary with image URL and public_id, or None if upload fails
        """
        try:
            # Default transformations for tour images
            if transformation is None:
                transformation = {
                    "width": 1200,
                    "height": 800,
                    "crop": "fill",
                    "quality": "auto:good",
                    "format": "webp"
                }
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file.file,
                folder=folder,
                transformation=transformation,
                resource_type="image",
                use_filename=True,
                unique_filename=True
            )
            
            logger.info(f"Successfully uploaded image: {result['public_id']}")
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "bytes": result.get("bytes")
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
            return None

    def upload_multiple_images(
        self, 
        files: List[UploadFile], 
        folder: str = "afro-nyanka-tours",
        transformation: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Upload multiple images to Cloudinary
        
        Args:
            files: List of FastAPI UploadFile objects
            folder: Cloudinary folder to store the images
            transformation: Optional transformation parameters
            
        Returns:
            List of dictionaries with image URLs and public_ids
        """
        uploaded_images = []
        
        for file in files:
            result = self.upload_image(file, folder, transformation)
            if result:
                uploaded_images.append(result)
        
        return uploaded_images

    def delete_image(self, public_id: str) -> bool:
        """
        Delete an image from Cloudinary
        
        Args:
            public_id: Cloudinary public_id of the image to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            if result.get("result") == "ok":
                logger.info(f"Successfully deleted image: {public_id}")
                return True
            else:
                logger.warning(f"Failed to delete image: {public_id}, result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting image {public_id}: {str(e)}")
            return False

    def delete_multiple_images(self, public_ids: List[str]) -> Dict[str, bool]:
        """
        Delete multiple images from Cloudinary
        
        Args:
            public_ids: List of Cloudinary public_ids to delete
            
        Returns:
            Dictionary mapping public_id to deletion success status
        """
        results = {}
        
        for public_id in public_ids:
            results[public_id] = self.delete_image(public_id)
        
        return results

    def get_image_url(
        self, 
        public_id: str, 
        transformation: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a Cloudinary URL for an image with optional transformations
        
        Args:
            public_id: Cloudinary public_id of the image
            transformation: Optional transformation parameters
            
        Returns:
            Cloudinary URL for the image
        """
        try:
            url, _ = cloudinary_url(public_id, transformation=transformation, secure=True)
            return url
        except Exception as e:
            logger.error(f"Error generating URL for {public_id}: {str(e)}")
            return ""

    def get_optimized_urls(self, public_id: str) -> Dict[str, str]:
        """
        Get optimized versions of an image for different use cases
        
        Args:
            public_id: Cloudinary public_id of the image
            
        Returns:
            Dictionary with different sized versions of the image
        """
        try:
            return {
                "thumbnail": self.get_image_url(public_id, {"width": 300, "height": 200, "crop": "fill", "quality": "auto:low"}),
                "medium": self.get_image_url(public_id, {"width": 600, "height": 400, "crop": "fill", "quality": "auto:good"}),
                "large": self.get_image_url(public_id, {"width": 1200, "height": 800, "crop": "fill", "quality": "auto:good"}),
                "original": self.get_image_url(public_id)
            }
        except Exception as e:
            logger.error(f"Error generating optimized URLs for {public_id}: {str(e)}")
            return {}

    def validate_image_file(self, file: UploadFile) -> bool:
        """
        Validate if the uploaded file is a valid image
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            True if file is a valid image, False otherwise
        """
        # Check file extension
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        file_extension = os.path.splitext(file.filename.lower())[1] if file.filename else ""
        
        if file_extension not in allowed_extensions:
            return False
        
        # Check content type
        allowed_content_types = {
            "image/jpeg", "image/jpg", "image/png", 
            "image/gif", "image/webp", "image/bmp"
        }
        
        if file.content_type not in allowed_content_types:
            return False
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if hasattr(file, 'size') and file.size and file.size > max_size:
            return False
        
        return True


# Global instance
cloudinary_service = CloudinaryService()
