from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://afro_user:afro_password@localhost:5432/afro_tours_db"
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    admin_email: Optional[str] = None
    
    # App settings
    debug: bool = True
    secret_key: str = "your-secret-key-here-change-in-production"
    
    class Config:
        env_file = ".env"


settings = Settings()
