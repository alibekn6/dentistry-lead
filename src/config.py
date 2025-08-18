"""Configuration settings for the dentistry lead generation system."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "postgresql://dentistry_user:dentistry_pass@localhost:5432/dentistry_db"
    
    # Scraping settings
    google_maps_api_key: Optional[str] = None
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Ignore extra fields from env
    }
    
    # Email settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""
    
    # Campaign settings
    seller_name: str = "Alex"
    company_name: str = "Premium Dental Solutions"
    test_mode: bool = True
    step_delay_seconds: int = 24  # 24 seconds for testing, 86400 for production (24 hours)
    
    # Scraping settings
    google_maps_api_key: Optional[str] = None  # Also reads GOOGLE_API_KEY from env
    scraping_delay_min: float = 1.0
    scraping_delay_max: float = 3.0
    max_retries: int = 3
    
    # Geography settings
    target_location: str = "London, UK"
    search_radius: int = 10000  # meters


# Global settings instance
settings = Settings()
