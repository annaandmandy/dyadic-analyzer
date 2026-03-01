"""Database models and session management."""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, index=True, nullable=False)
    dominant_person = Column(Integer, nullable=False)
    interaction_strength = Column(Integer, nullable=False)
    mutual_attention = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(String, unique=True, index=True, nullable=False)
    result_json = Column(String, nullable=False)
    dominance_score_0 = Column(Float)
    dominance_score_1 = Column(Float)
    engagement_score = Column(Float)
    mutual_gaze = Column(Boolean)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TunedWeights(Base):
    __tablename__ = "tuned_weights"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    weights_json = Column(String, nullable=False)
    metrics_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
