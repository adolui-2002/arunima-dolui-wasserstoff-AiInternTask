"""
Database models for the email assistant.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from email_assistant.config import settings
from datetime import datetime

# Create the SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL)

# Create a session factory
session_factory = sessionmaker(bind=engine)

# Create a scoped session
db = scoped_session(session_factory)

# Create base class
Base = declarative_base()
Base.query = db.query_property()

class Email(Base):
    """Email model for storing email data."""
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, nullable=False)
    message_id = Column(String, unique=True, nullable=False)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    body = Column(String, nullable=False)
    is_important = Column(Boolean, default=False)
    priority = Column(String, default='normal')
    intent = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    status = Column(String, default='unread')
    no_response = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attachments = relationship("Attachment", back_populates="email")
    meeting = relationship("Meeting", back_populates="email", uselist=False)

class Attachment(Base):
    """Model for storing email attachments."""
    __tablename__ = 'attachments'

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey('emails.id'))
    filename = Column(String(255))
    content_type = Column(String(100))
    size = Column(Integer)
    storage_path = Column(String(255))

    # Relationships
    email = relationship("Email", back_populates="attachments")

class Meeting(Base):
    __tablename__ = 'meetings'

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey('emails.id'))
    title = Column(String(255))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    location = Column(String(255))
    description = Column(Text)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    email = relationship("Email", back_populates="meeting")

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)