"""
Database models for pickmychild bot
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime
from typing import List


class User(Base):
    """Telegram user"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    people = relationship("Person", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Person(Base):
    """Person in user's list"""
    __tablename__ = "people"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="people")
    examples = relationship("PersonExample", back_populates="person", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Person(id={self.id}, name={self.name})>"


class PersonExample(Base):
    """Example images for a person (used to generate embeddings)"""
    __tablename__ = "person_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    telegram_file_id = Column(String, nullable=True)
    embedding = Column(LargeBinary, nullable=True)  # Stored as numpy array bytes
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    person = relationship("Person", back_populates="examples")
    
    def __repr__(self):
        return f"<PersonExample(id={self.id}, person_id={self.person_id})>"


class Event(Base):
    """Event/Wedding with uploaded photos"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # EVT-XXXXX
    creator_telegram_id = Column(Integer, nullable=False, index=True)
    
    # Status: UPLOADING, PROCESSING, READY, FAILED
    status = Column(String, default="UPLOADING", nullable=False)
    
    # Processing progress (0-100)
    progress = Column(Integer, default=0)
    progress_message = Column(Text, nullable=True)  # "① פירוק ZIP (35%)"
    
    # Metadata
    total_images = Column(Integer, default=0)
    processed_images = Column(Integer, default=0)
    zip_file_path = Column(String, nullable=True)
    faiss_index_path = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    ready_at = Column(DateTime, nullable=True)
    
    # Relationships
    images = relationship("EventImage", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Event(code={self.code}, status={self.status}, progress={self.progress}%)>"


class EventImage(Base):
    """Individual image in an event"""
    __tablename__ = "event_images"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    
    file_path = Column(String, nullable=False)
    telegram_file_id = Column(String, nullable=True)  # After upload to Telegram
    
    # Face detection results
    has_faces = Column(Boolean, default=False)
    num_faces = Column(Integer, default=0)
    embeddings = Column(LargeBinary, nullable=True)  # List of embeddings for all faces
    
    # Metadata
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="images")
    
    def __repr__(self):
        return f"<EventImage(id={self.id}, event_id={self.event_id}, has_faces={self.has_faces})>"


class UserState(Base):
    """Track user conversation state for multi-step flows"""
    __tablename__ = "user_states"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # State: None, ADDING_PERSON, ENTERING_EVENT_CODE, etc.
    state = Column(String, nullable=True)
    
    # Context data (JSON as string)
    context = Column(Text, nullable=True)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserState(telegram_id={self.telegram_id}, state={self.state})>"
