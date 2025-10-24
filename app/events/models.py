"""SQLAlchemy models for events."""

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.sql import func
from db import Base


class Event(Base):
    """Event model for presence check results."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False)
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    geofence_id = Column(
        Integer, ForeignKey("geofences.id", ondelete="SET NULL"), nullable=True
    )
    method = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
