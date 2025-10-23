"""Pydantic schemas for events."""
from typing import Optional, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict  # v2

# You defined your own enums (good). Keeping them:
class EventStatus(str, Enum):
    """Event status enumeration."""
    present = "present"
    late = "late"
    absent = "absent"
    outside = "outside"

class EventMethod(str, Enum):
    """Event method enumeration."""
    manual = "manual"
    auto = "auto"

class EventBase(BaseModel):
    """Base schema for event data."""
    status: EventStatus = Field(..., description="Status de présence")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    geofence_id: Optional[int] = Field(None, description="ID de la géofence")
    method: EventMethod = Field(..., description="Méthode de vérification")

class EventCreate(EventBase):
    """Schema for creating an event."""
    student_id: int = Field(..., description="ID de l'étudiant")

# ✅ Add this to satisfy imports from routes
class EventUpdate(BaseModel):
    """Partial update for an event; all fields optional."""
    status: Optional[EventStatus] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    geofence_id: Optional[int] = None
    method: Optional[EventMethod] = None

class EventResponse(EventBase):
    """Schema for event response."""
    id: int
    student_id: int
    created_at: datetime

    # pydantic v2 config
    model_config = ConfigDict(from_attributes=True)

class EventListResponse(BaseModel):
    """Schema for event list response."""
    events: List[EventResponse]
    total: int
    limit: int
    offset: int

class EventQueryParams(BaseModel):
    """Schema for event query parameters."""
    matricule: Optional[str] = Field(None, description="Matricule de l'étudiant")
    from_date: Optional[datetime] = Field(None, description="Date de début (ISO format)")
    to_date: Optional[datetime] = Field(None, description="Date de fin (ISO format)")
    limit: int = Field(50, ge=1, le=100, description="Nombre d'éléments par page")
    offset: int = Field(0, ge=0, description="Décalage pour la pagination")

class DailyStatsResponse(BaseModel):
    """Schema for daily statistics response."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    total_events: int = Field(..., description="Nombre total d'événements")
    present_count: int = Field(..., description="Nombre de présents")
    late_count: int = Field(..., description="Nombre de retards")
    absent_count: int = Field(..., description="Nombre d'absents")
    outside_count: int = Field(..., description="Nombre d'extérieurs")
    manual_count: int = Field(..., description="Nombre de vérifications manuelles")
    auto_count: int = Field(..., description="Nombre de vérifications automatiques")

class EventWithStudentResponse(EventResponse):
    """Schema for event response with student information."""
    student_matricule: str = Field(..., description="Matricule de l'étudiant")
    student_nom: str = Field(..., description="Nom de l'étudiant")
    student_prenom: str = Field(..., description="Prénom de l'étudiant")
    geofence_name: Optional[str] = Field(None, description="Nom de la géofence")
