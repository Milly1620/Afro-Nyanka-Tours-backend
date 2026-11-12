import os
from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Optional


DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"
MIN_SECRET_KEY_LENGTH = 32


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
    cron_secret: Optional[str] = None  # shared secret for the weekly-summary cron call
    cors_origins: str = "*"  # comma-separated list of allowed origins

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]

    @model_validator(mode="after")
    def _require_real_config_in_prod(self):
        if self.debug:
            return self
        if self.secret_key == DEFAULT_SECRET_KEY or len(self.secret_key or "") < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be a real secret of at least {MIN_SECRET_KEY_LENGTH} characters when DEBUG is false"
            )
        if not (self.frontend_url or "").strip():
            raise ValueError("FRONTEND_URL must be set when DEBUG is false (used in admin password links)")
        return self
    
    class Config:
        env_file = ".env"


settings = Settings()
