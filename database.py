from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meeting_intelligence.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    audio_filename = Column(String)
    transcription = Column(Text)
    summary = Column(Text)
    action_items = Column(JSON)
    decisions = Column(JSON)
    visual_summary_url = Column(String)
    embedding = Column(JSON)  # Store as JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    language = Column(String, default="en")


class Translation(Base):
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, index=True)
    target_language = Column(String)
    translated_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()