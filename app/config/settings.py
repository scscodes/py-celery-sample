"""
Application settings and configuration management.

This module centralizes all application configuration using Pydantic settings
for type validation and environment variable handling.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Main application settings class.
    
    Uses Pydantic BaseSettings to automatically load configuration from:
    1. Environment variables
    2. .env file  
    3. Default values defined here
    """
    
    # Database Configuration
    database_url: str = "sqlite:///./celery_showcase.db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery Configuration  
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Application Configuration
    debug: bool = True
    log_level: str = "INFO"
    
    # API Configuration
    api_v1_str: str = "/api/v1"
    project_name: str = "Celery Showcase"
    
    # Flower Monitoring Configuration
    flower_port: int = 5555
    flower_broker_api: Optional[str] = None
    
    class Config:
        """Pydantic configuration for settings loading."""
        env_file = ".env"
        case_sensitive = False


# Global settings instance
# This will be imported throughout the application for configuration access
settings = Settings()
