"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import time
from enum import Enum

class MethodEnum(str, Enum):
    """Method for presence check."""
    auto = "auto"
    manual = "manual"

class StatusEnum(str, Enum):
    """Attendance status."""
    present = "present"
    late = "late"
    absent = "absent"
    outside = "outside"

# Geofence schemas
class GeofenceCreate(BaseModel):
    """Schema for creating/updating geofence."""
    name: str = Field(..., description="Nom de la géofence")
    polygon: Dict[str, Any] = Field(..., description="GeoJSON polygon")
    margin_m: int = Field(default=0, description="Marge en mètres")

class GeofenceResponse(BaseModel):
    """Schema for geofence response."""
    id: int
    name: str
    polygon: Dict[str, Any]
    margin_m: int
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Time window schemas
class TimeWindowCreate(BaseModel):
    """Schema for creating time window."""
    name: str = Field(..., description="Nom de la fenêtre horaire")
    start_time: time = Field(..., description="Heure de début")
    end_time: time = Field(..., description="Heure de fin")

class TimeWindowResponse(BaseModel):
    """Schema for time window response."""
    id: int
    name: str
    start_time: str
    end_time: str
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Presence check schemas
class PresenceCheckRequest(BaseModel):
    """Schema for presence check request."""
    matricule: str = Field(..., description="Matricule de l'étudiant")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    accuracy: Optional[float] = Field(None, description="Précision en mètres")
    method: MethodEnum = Field(..., description="Méthode de vérification")

class PresenceCheckResponse(BaseModel):
    """Schema for presence check response."""
    status: StatusEnum
    message: str
    time_window: Optional[str] = None
    geofence: Optional[str] = None
    event_id: Optional[int] = None

# Auth schemas
class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str

class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"

