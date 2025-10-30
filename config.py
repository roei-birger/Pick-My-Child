"""
Configuration and settings for pickmychild bot
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Telegram Bot
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    
    # Database
    database_url: str = Field(default="sqlite:///./pickmychild.db", alias="DATABASE_URL")
    
    # AI Configuration
    face_detection_confidence: float = Field(default=0.6, alias="FACE_DETECTION_CONFIDENCE")
    face_match_threshold: float = Field(default=0.80, alias="FACE_MATCH_THRESHOLD")
    min_face_size: int = Field(default=20, alias="MIN_FACE_SIZE")
    
    # Event Processing
    max_zip_size_mb: int = Field(default=500, alias="MAX_ZIP_SIZE_MB")
    event_retention_days: int = Field(default=30, alias="EVENT_RETENTION_DAYS")
    batch_size: int = Field(default=10, alias="BATCH_SIZE")
    
    # Paths
    upload_dir: Path = Field(default=Path("./uploads"), alias="UPLOAD_DIR")
    event_data_dir: Path = Field(default=Path("./event_data"), alias="EVENT_DATA_DIR")
    models_dir: Path = Field(default=Path("./models"), alias="MODELS_DIR")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Path = Field(default=Path("./logs/bot.log"), alias="LOG_FILE")
    
    # Feature Flags
    enable_events_feature: bool = Field(default=False, alias="ENABLE_EVENTS_FEATURE")
    
    # Photo Processing
    photo_accumulation_timeout: float = Field(default=3.0, alias="PHOTO_ACCUMULATION_TIMEOUT")
    
    # Person Management
    min_photos_per_person: int = 5
    max_photos_per_person: int = 20
    recommended_photos: int = 5
    
    # Event Codes
    event_code_prefix: str = "EVT"
    event_code_length: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create global settings instance
settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.event_data_dir.mkdir(parents=True, exist_ok=True)
settings.models_dir.mkdir(parents=True, exist_ok=True)
settings.log_file.parent.mkdir(parents=True, exist_ok=True)
