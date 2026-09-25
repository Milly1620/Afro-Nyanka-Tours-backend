import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str 
    
    # Email settings
    brevo_api_key: Optional[str] = None
    sender_email: str = "info@afronyankatours.com"
    sender_name: str = "Afro Nyanka Tours"
    admin_email: Optional[str] = None
    
    # Cloudinary settings
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None

    # App settings
    debug: bool = False
    secret_key: str = "your-secret-key-here-change-in-production"
    
    class Config:
        env_file = ".env"


settings = Settings()
