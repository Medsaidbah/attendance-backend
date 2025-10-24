"""Pydantic schemas for students."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class StudentBase(BaseModel):
    """Base schema for student data."""

    matricule: str = Field(
        ..., min_length=1, max_length=50, description="Matricule de l'étudiant"
    )
    nom: str = Field(..., min_length=1, max_length=100, description="Nom de famille")
    prenom: str = Field(..., min_length=1, max_length=100, description="Prénom")
    is_active: bool = Field(default=True, description="Statut actif")

    @validator("matricule")
    def validate_matricule(cls, v):
        """Validate matricule format."""
        if not v or not v.strip():
            raise ValueError("Le matricule ne peut pas être vide")
        return v.strip().upper()

    @validator("nom", "prenom")
    def validate_names(cls, v):
        """Validate name format."""
        if not v or not v.strip():
            raise ValueError("Le nom et prénom ne peuvent pas être vides")
        return v.strip().title()


class StudentCreate(StudentBase):
    """Schema for creating a student."""

    pass


class StudentUpdate(BaseModel):
    """Schema for updating a student."""

    nom: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Nom de famille"
    )
    prenom: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Prénom"
    )
    is_active: Optional[bool] = Field(None, description="Statut actif")

    @validator("nom", "prenom")
    def validate_names(cls, v):
        """Validate name format."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Le nom et prénom ne peuvent pas être vides")
        return v.strip().title() if v else v


class StudentResponse(StudentBase):
    """Schema for student response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    """Schema for paginated student list response."""

    students: List[StudentResponse]
    total: int
    limit: int
    offset: int


class StudentImportRow(BaseModel):
    """Schema for CSV import row."""

    matricule: str = Field(..., description="Matricule")
    nom: str = Field(..., description="Nom")
    prenom: str = Field(..., description="Prénom")

    @validator("matricule")
    def validate_matricule(cls, v):
        """Validate matricule format."""
        if not v or not v.strip():
            raise ValueError("Le matricule ne peut pas être vide")
        return v.strip().upper()

    @validator("nom", "prenom")
    def validate_names(cls, v):
        """Validate name format."""
        if not v or not v.strip():
            raise ValueError("Le nom et prénom ne peuvent pas être vides")
        return v.strip().title()


class StudentImportResponse(BaseModel):
    """Schema for import response."""

    success_count: int
    error_count: int
    errors: List[str]
    message: str
