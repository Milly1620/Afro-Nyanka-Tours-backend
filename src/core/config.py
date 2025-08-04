import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str 
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    admin_email: Optional[str] = None
    
    # App settings
    debug: bool = False
    secret_key: str = "your-secret-key-here-change-in-production"
    
    class Config:
        env_file = ".env"


settings = Settings()
