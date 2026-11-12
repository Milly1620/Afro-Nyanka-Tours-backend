import os
from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Optional


DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"


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
    secret_key: str = DEFAULT_SECRET_KEY

    # Admin portal
    admin_emails: str = ""  # comma-separated; synced to admin_users on startup
    frontend_url: str = "http://localhost:3000"
    cron_secret: Optional[str] = None
    cors_origins: str = "*"  # comma-separated list of allowed origins

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]

    @model_validator(mode="after")
    def _reject_default_secret_in_prod(self):
        if not self.debug and self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError("SECRET_KEY must be set to a real secret when DEBUG is false")
        return self
    
    class Config:
        env_file = ".env"


settings = Settings()
