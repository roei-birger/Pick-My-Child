"""
Storage Service - File management for uploads, events, and images
"""
import shutil
from pathlib import Path
from typing import Optional
import hashlib
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Manage file storage for the bot"""
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.event_data_dir = settings.event_data_dir
        
        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.event_data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_file(
        self,
        file_content: bytes,
        user_id: int,
        file_extension: str = ".jpg"
    ) -> Path:
        """
        Save uploaded file
        
        Returns:
            Path to saved file
        """
        # Create user directory
        user_dir = self.upload_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        filename = f"{timestamp}_{file_hash}{file_extension}"
        
        file_path = user_dir / filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved uploaded file: {file_path}")
        
        return file_path
    
    def save_person_example(
        self,
        file_content: bytes,
        user_id: int,
        person_id: int,
        file_extension: str = ".jpg"
    ) -> Path:
        """Save person example image"""
        # Create person directory
        person_dir = self.upload_dir / str(user_id) / "people" / str(person_id)
        person_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        filename = f"example_{timestamp}_{file_hash}{file_extension}"
        
        file_path = person_dir / filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved person example: {file_path}")
        
        return file_path
    
    def save_event_zip(
        self,
        file_content: bytes,
        event_code: str
    ) -> Path:
        """Save event ZIP file"""
        event_dir = self.event_data_dir / event_code
        event_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = event_dir / "event.zip"
        
        with open(zip_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved event ZIP: {zip_path} ({len(file_content) / 1024 / 1024:.2f} MB)")
        
        return zip_path
    
    def delete_person_files(self, user_id: int, person_id: int):
        """Delete all files for a person"""
        person_dir = self.upload_dir / str(user_id) / "people" / str(person_id)
        
        if person_dir.exists():
            shutil.rmtree(person_dir)
            logger.info(f"Deleted person directory: {person_dir}")
    
    def delete_event_files(self, event_code: str):
        """Delete all files for an event"""
        event_dir = self.event_data_dir / event_code
        
        if event_dir.exists():
            shutil.rmtree(event_dir)
            logger.info(f"Deleted event directory: {event_dir}")
    
    def delete_user_files(self, user_id: int):
        """Delete all files for a user"""
        user_dir = self.upload_dir / str(user_id)
        
        if user_dir.exists():
            shutil.rmtree(user_dir)
            logger.info(f"Deleted user directory: {user_dir}")
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    def validate_zip_size(self, file_size_bytes: int) -> bool:
        """Check if ZIP file size is within limits"""
        max_size_bytes = settings.max_zip_size_mb * 1024 * 1024
        return file_size_bytes <= max_size_bytes


# Global storage service instance
storage_service = StorageService()
