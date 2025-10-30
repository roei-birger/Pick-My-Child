"""
Event Processor - Asynchronous processing of event ZIP files
"""
import asyncio
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Callable
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from config import settings
from models import Event, EventImage
from services.ai_service import ai_service
import numpy as np

logger = logging.getLogger(__name__)


class EventProcessor:
    """Process event ZIP files asynchronously"""
    
    def __init__(self):
        self.processing_tasks = {}  # event_code -> Task
    
    async def process_event(
        self,
        event_code: str,
        zip_path: str,
        db: Session,
        progress_callback: Optional[Callable] = None
    ):
        """
        Process event ZIP file asynchronously
        
        Args:
            event_code: Event code (EVT-XXXXX)
            zip_path: Path to ZIP file
            db: Database session
            progress_callback: Callback function for progress updates (event_code, progress, message)
        """
        try:
            logger.info(f"Starting processing for event {event_code}")
            
            # Get event from DB
            event = db.query(Event).filter(Event.code == event_code).first()
            if not event:
                logger.error(f"Event {event_code} not found in database")
                return
            
            # Update status
            event.status = "PROCESSING"
            event.progress = 0
            db.commit()
            
            # Step 1: Extract ZIP (0-30%)
            await self._update_progress(event, db, 5, "① פירוק ZIP...", progress_callback)
            
            extract_dir = settings.event_data_dir / event_code
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            image_files = await self._extract_zip(zip_path, extract_dir)
            event.total_images = len(image_files)
            db.commit()
            
            await self._update_progress(event, db, 30, f"① פירוק ZIP הושלם - {len(image_files)} תמונות", progress_callback)
            
            # Step 2: Face detection and embedding (30-90%)
            await self._update_progress(event, db, 30, "② זיהוי פנים...", progress_callback)
            
            all_embeddings = []
            embedding_to_image_id = []
            
            for idx, image_file in enumerate(image_files):
                # Process image
                faces = ai_service.detect_faces(str(image_file))
                
                # Create EventImage record
                event_image = EventImage(
                    event_id=event.id,
                    file_path=str(image_file),
                    has_faces=len(faces) > 0,
                    num_faces=len(faces),
                    processed=True
                )
                
                if faces:
                    # Store embeddings
                    embeddings_list = [face['embedding'] for face in faces]
                    event_image.embeddings = pickle.dumps(embeddings_list)
                    
                    # Collect for FAISS index
                    for embedding in embeddings_list:
                        all_embeddings.append(embedding)
                        embedding_to_image_id.append(event_image.id)
                
                db.add(event_image)
                
                # Update progress every 10 images
                if (idx + 1) % 10 == 0 or (idx + 1) == len(image_files):
                    event.processed_images = idx + 1
                    progress = 30 + int((idx + 1) / len(image_files) * 60)
                    message = f"② זיהוי פנים ({idx + 1}/{len(image_files)})"
                    await self._update_progress(event, db, progress, message, progress_callback)
            
            db.commit()
            
            # Step 3: Build FAISS index (90-100%)
            await self._update_progress(event, db, 90, "③ בניית אינדקס חיפוש...", progress_callback)
            
            if all_embeddings:
                # Create FAISS index
                index, _ = ai_service.create_faiss_index(all_embeddings)
                
                # Save index
                index_path = extract_dir / "faiss.index"
                ai_service.save_index(index, str(index_path))
                event.faiss_index_path = str(index_path)
                
                # Save mapping
                mapping_path = extract_dir / "embedding_mapping.pkl"
                with open(mapping_path, 'wb') as f:
                    pickle.dump(embedding_to_image_id, f)
                
                logger.info(f"Built FAISS index with {len(all_embeddings)} embeddings for event {event_code}")
            
            # Complete
            event.status = "READY"
            event.progress = 100
            event.progress_message = "✅ מוכן!"
            event.ready_at = datetime.utcnow()
            db.commit()
            
            await self._update_progress(event, db, 100, "✅ מוכן!", progress_callback)
            
            logger.info(f"Event {event_code} processing completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing event {event_code}: {e}", exc_info=True)
            
            # Update event status
            event = db.query(Event).filter(Event.code == event_code).first()
            if event:
                event.status = "FAILED"
                event.progress_message = f"שגיאה: {str(e)}"
                db.commit()
            
            if progress_callback:
                await progress_callback(event_code, -1, f"❌ שגיאה: {str(e)}")
    
    async def _extract_zip(self, zip_path: str, extract_dir: Path) -> list:
        """Extract ZIP and return list of image files"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        image_files = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract all
                zip_ref.extractall(extract_dir)
            
            # Find all image files
            for file_path in extract_dir.rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
            
            logger.info(f"Extracted {len(image_files)} images from ZIP")
            return image_files
            
        except Exception as e:
            logger.error(f"Error extracting ZIP: {e}")
            raise
    
    async def _update_progress(
        self,
        event: Event,
        db: Session,
        progress: int,
        message: str,
        callback: Optional[Callable]
    ):
        """Update event progress"""
        event.progress = progress
        event.progress_message = message
        db.commit()
        
        if callback:
            await callback(event.code, progress, message)
        
        # Small delay to prevent flooding
        await asyncio.sleep(0.1)
    
    def start_processing(
        self,
        event_code: str,
        zip_path: str,
        db: Session,
        progress_callback: Optional[Callable] = None
    ):
        """Start processing task in background"""
        # Create task
        task = asyncio.create_task(
            self.process_event(event_code, zip_path, db, progress_callback)
        )
        
        self.processing_tasks[event_code] = task
        
        logger.info(f"Started background processing for event {event_code}")
        
        return task
    
    def get_processing_status(self, event_code: str) -> Optional[str]:
        """Get processing task status"""
        if event_code in self.processing_tasks:
            task = self.processing_tasks[event_code]
            
            if task.done():
                return "COMPLETED"
            else:
                return "PROCESSING"
        
        return None


# Global event processor instance
event_processor = EventProcessor()


import pickle
