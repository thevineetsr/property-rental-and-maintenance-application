import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Property Rental & Maintenance Management System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite:///./property_rental.db"
    
    JWT_SECRET_KEY: str = "super-secret-jwt-key-replace-in-production-takehome-07"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    GRACE_PERIOD_DAYS: int = 5  # Rent overdue after 5th of month

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
