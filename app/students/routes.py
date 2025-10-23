"""FastAPI routes for students."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from db import get_db
from auth import get_current_user
from students.service import StudentService  # absolute import avoids confusion

from students.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentListResponse,
    StudentImportResponse,
)


router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=StudentListResponse)
async def get_students(
    q: Optional[str] = Query(None, description="Recherche par matricule, nom ou prénom"),
    limit: int = Query(50, ge=1, le=100, description="Nombre d'éléments par page"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: Session = Depends(get_db),
):
    """Récupérer la liste des étudiants avec pagination et recherche."""
    service = StudentService(db)
    students, total = service.get_students(q=q, limit=limit, offset=offset)

    return StudentListResponse(students=students, total=total, limit=limit, offset=offset)


@router.post("", response_model=StudentResponse, status_code=201)
async def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Créer un nouvel étudiant."""
    service = StudentService(db)
    return service.create_student(student_data)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    """Récupérer un étudiant par son ID."""
    service = StudentService(db)
    student = service.get_student_by_id(student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Étudiant non trouvé")

    return student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    student_data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Mettre à jour un étudiant."""
    service = StudentService(db)
    return service.update_student(student_id, student_data)


@router.delete("/{student_id}", status_code=204)
async def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Supprimer un étudiant (suppression logique)."""
    service = StudentService(db)
    service.soft_delete_student(student_id)
    return None


@router.post("/import", response_model=StudentImportResponse)
async def import_students(
    file: UploadFile = File(..., description="Fichier CSV avec colonnes: matricule,nom,prenom"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Importer des étudiants depuis un fichier CSV."""
    # Read file asynchronously here
    content = await file.read()
    # Pass bytes to the *sync* service method
    service = StudentService(db)
    return service.import_students_csv(content)
