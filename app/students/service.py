"""Business logic for students."""

import csv
import io
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, UploadFile

from students.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentImportRow,
    StudentImportResponse,
)


class StudentService:
    """Service class for student operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_students(
        self, q: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[dict], int]:
        """Get students with pagination and search."""
        search_condition = ""
        params = {"limit": limit, "offset": offset}

        if q:
            search_condition = """
                AND (LOWER(matricule) LIKE LOWER(:q) 
                     OR LOWER(nom) LIKE LOWER(:q) 
                     OR LOWER(prenom) LIKE LOWER(:q))
            """
            params["q"] = f"%{q}%"

        count_query = f"""
            SELECT COUNT(*) as total
            FROM students 
            WHERE is_active = true {search_condition}
        """
        total_result = self.db.execute(text(count_query), params).fetchone()
        total = total_result.total if total_result else 0

        students_query = f"""
            SELECT id, matricule, nom, prenom, is_active, created_at, updated_at
            FROM students 
            WHERE is_active = true {search_condition}
            ORDER BY nom, prenom
            LIMIT :limit OFFSET :offset
        """
        students = self.db.execute(text(students_query), params).fetchall()

        return [
            {
                "id": s.id,
                "matricule": s.matricule,
                "nom": s.nom,
                "prenom": s.prenom,
                "is_active": s.is_active,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in students
        ], total

    def get_student_by_id(self, student_id: int) -> Optional[dict]:
        """Get student by ID."""
        result = self.db.execute(
            text(
                """
                SELECT id, matricule, nom, prenom, is_active, created_at, updated_at
                FROM students 
                WHERE id = :id
                """
            ),
            {"id": student_id},
        ).fetchone()

        if not result:
            return None

        return {
            "id": result.id,
            "matricule": result.matricule,
            "nom": result.nom,
            "prenom": result.prenom,
            "is_active": result.is_active,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
        }

    def get_student_by_matricule(self, matricule: str) -> Optional[dict]:
        """Get student by matricule."""
        result = self.db.execute(
            text(
                """
                SELECT id, matricule, nom, prenom, is_active, created_at, updated_at
                FROM students 
                WHERE matricule = :matricule
                """
            ),
            {"matricule": matricule},
        ).fetchone()

        if not result:
            return None

        return {
            "id": result.id,
            "matricule": result.matricule,
            "nom": result.nom,
            "prenom": result.prenom,
            "is_active": result.is_active,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
        }

    def create_student(self, student_data: StudentCreate) -> dict:
        """Create a new student."""
        existing = self.get_student_by_matricule(student_data.matricule)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Un étudiant avec le matricule '{student_data.matricule}' existe déjà",
            )

        try:
            result = self.db.execute(
                text(
                    """
                    INSERT INTO students (matricule, nom, prenom, is_active)
                    VALUES (:matricule, :nom, :prenom, :is_active)
                    RETURNING id, created_at, updated_at
                    """
                ),
                {
                    "matricule": student_data.matricule,
                    "nom": student_data.nom,
                    "prenom": student_data.prenom,
                    "is_active": student_data.is_active,
                },
            )
            new_student = result.fetchone()
            self.db.commit()

            return {
                "id": new_student.id,
                "matricule": student_data.matricule,
                "nom": student_data.nom,
                "prenom": student_data.prenom,
                "is_active": student_data.is_active,
                "created_at": new_student.created_at,
                "updated_at": new_student.updated_at,
            }
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=400, detail=f"Erreur lors de la création: {str(e)}"
            )

    def update_student(self, student_id: int, student_data: StudentUpdate) -> dict:
        """Update a student."""
        existing = self.get_student_by_id(student_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")

        update_fields = []
        params = {"id": student_id}

        if student_data.nom is not None:
            update_fields.append("nom = :nom")
            params["nom"] = student_data.nom
        if student_data.prenom is not None:
            update_fields.append("prenom = :prenom")
            params["prenom"] = student_data.prenom
        if student_data.is_active is not None:
            update_fields.append("is_active = :is_active")
            params["is_active"] = student_data.is_active

        if not update_fields:
            return existing

        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        try:
            self.db.execute(
                text(
                    f"""
                    UPDATE students 
                    SET {', '.join(update_fields)}
                    WHERE id = :id
                    """
                ),
                params,
            )
            self.db.commit()
            return self.get_student_by_id(student_id)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}"
            )

    def soft_delete_student(self, student_id: int) -> bool:
        """Soft delete a student (set is_active=False)."""
        existing = self.get_student_by_id(student_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")

        try:
            self.db.execute(
                text(
                    """
                    UPDATE students 
                    SET is_active = false, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": student_id},
            )
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=400, detail=f"Erreur lors de la suppression: {str(e)}"
            )

    # ---------- CSV import helpers ----------

    def import_students_csv_content(self, content: bytes) -> StudentImportResponse:
        """
        Import students from raw CSV bytes (used by routes).
        Validates required headers; returns a summary response object.
        """
        try:
            csv_text = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(csv_text))

            required = {"matricule", "nom", "prenom"}
            headers = set(reader.fieldnames or [])
            if not required.issubset(headers):
                missing = required - headers
                raise HTTPException(
                    status_code=400,
                    detail=f"Colonnes manquantes dans le CSV: {', '.join(missing)}",
                )

            success_count = 0
            error_count = 0
            errors: List[str] = []

            for idx, row in enumerate(reader, start=2):
                try:
                    parsed = StudentImportRow(
                        matricule=row.get("matricule", ""),
                        nom=row.get("nom", ""),
                        prenom=row.get("prenom", ""),
                    )

                    if self.get_student_by_matricule(parsed.matricule):
                        error_count += 1
                        errors.append(
                            f"Ligne {idx}: Matricule '{parsed.matricule}' existe déjà"
                        )
                        continue

                    data = StudentCreate(
                        matricule=parsed.matricule,
                        nom=parsed.nom,
                        prenom=parsed.prenom,
                        is_active=True,
                    )
                    self.create_student(data)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Ligne {idx}: {str(e)}")

            return StudentImportResponse(
                success_count=success_count,
                error_count=error_count,
                errors=errors,
                message=f"Import terminé: {success_count} étudiants créés, {error_count} erreurs",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Erreur lors de l'import: {str(e)}"
            )

    async def import_students_csv(
        self, upload_file: UploadFile
    ) -> StudentImportResponse:
        """
        Async CSV import used by tests.
        - Must raise "Le fichier doit être un CSV" for bad extension
        - Must raise "Colonnes manquantes" when headers are missing
        - Returns StudentImportResponse with success/error counts
        """
        if not upload_file or not str(upload_file.filename).lower().endswith(".csv"):
            raise Exception("Le fichier doit être un CSV")

        raw = await upload_file.read()
        text_csv = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text_csv))

        required = {"matricule", "nom", "prenom"}
        headers = set(reader.fieldnames or [])
        if not required.issubset(headers):
            raise Exception("Colonnes manquantes")

        success_count = 0
        error_count = 0
        errors: List[str] = []

        for idx, row in enumerate(reader, start=2):  # header is line 1
            matricule = (row.get("matricule") or "").strip()
            nom = (row.get("nom") or "").strip()
            prenom = (row.get("prenom") or "").strip()

            if not matricule:
                error_count += 1
                errors.append(f"Ligne {idx}: Matricule manquant")
                continue

            if self.get_student_by_matricule(matricule):
                error_count += 1
                errors.append(f"Ligne {idx}: Matricule '{matricule}' existe déjà")
                continue

            data = StudentCreate(
                matricule=matricule, nom=nom, prenom=prenom, is_active=True
            )
            # tests monkeypatch this to avoid touching a real DB
            self.create_student(data)
            success_count += 1

        return StudentImportResponse(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            message=f"Import terminé: {success_count} étudiants créés, {error_count} erreurs",
        )
