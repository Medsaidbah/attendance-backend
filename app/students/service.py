"""Business logic for students."""
import csv
import io
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

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
        self, 
        q: Optional[str] = None, 
        limit: int = 50, 
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        """Get students with pagination and search."""
        # Build search condition
        search_condition = ""
        params = {"limit": limit, "offset": offset}
        
        if q:
            search_condition = """
                AND (LOWER(matricule) LIKE LOWER(:q) 
                     OR LOWER(nom) LIKE LOWER(:q) 
                     OR LOWER(prenom) LIKE LOWER(:q))
            """
            params["q"] = f"%{q}%"
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM students 
            WHERE is_active = true {search_condition}
        """
        total_result = self.db.execute(text(count_query), params).fetchone()
        total = total_result.total if total_result else 0
        
        # Get students
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
                "id": student.id,
                "matricule": student.matricule,
                "nom": student.nom,
                "prenom": student.prenom,
                "is_active": student.is_active,
                "created_at": student.created_at,
                "updated_at": student.updated_at
            }
            for student in students
        ], total
    
    def get_student_by_id(self, student_id: int) -> Optional[dict]:
        """Get student by ID."""
        result = self.db.execute(text("""
            SELECT id, matricule, nom, prenom, is_active, created_at, updated_at
            FROM students 
            WHERE id = :id
        """), {"id": student_id}).fetchone()
        
        if not result:
            return None
        
        return {
            "id": result.id,
            "matricule": result.matricule,
            "nom": result.nom,
            "prenom": result.prenom,
            "is_active": result.is_active,
            "created_at": result.created_at,
            "updated_at": result.updated_at
        }
    
    def get_student_by_matricule(self, matricule: str) -> Optional[dict]:
        """Get student by matricule."""
        result = self.db.execute(text("""
            SELECT id, matricule, nom, prenom, is_active, created_at, updated_at
            FROM students 
            WHERE matricule = :matricule
        """), {"matricule": matricule}).fetchone()
        
        if not result:
            return None
        
        return {
            "id": result.id,
            "matricule": result.matricule,
            "nom": result.nom,
            "prenom": result.prenom,
            "is_active": result.is_active,
            "created_at": result.created_at,
            "updated_at": result.updated_at
        }
    
    def create_student(self, student_data: StudentCreate) -> dict:
        """Create a new student."""
        # Check if matricule already exists
        existing = self.get_student_by_matricule(student_data.matricule)
        if existing:
            raise HTTPException(
                status_code=409, 
                detail=f"Un étudiant avec le matricule '{student_data.matricule}' existe déjà"
            )
        
        try:
            result = self.db.execute(text("""
                INSERT INTO students (matricule, nom, prenom, is_active)
                VALUES (:matricule, :nom, :prenom, :is_active)
                RETURNING id, created_at, updated_at
            """), {
                "matricule": student_data.matricule,
                "nom": student_data.nom,
                "prenom": student_data.prenom,
                "is_active": student_data.is_active
            })
            
            new_student = result.fetchone()
            self.db.commit()
            
            return {
                "id": new_student.id,
                "matricule": student_data.matricule,
                "nom": student_data.nom,
                "prenom": student_data.prenom,
                "is_active": student_data.is_active,
                "created_at": new_student.created_at,
                "updated_at": new_student.updated_at
            }
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Erreur lors de la création: {str(e)}")
    
    def update_student(self, student_id: int, student_data: StudentUpdate) -> dict:
        """Update a student."""
        # Check if student exists
        existing = self.get_student_by_id(student_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")
        
        # Build update query dynamically
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
            self.db.execute(text(f"""
                UPDATE students 
                SET {', '.join(update_fields)}
                WHERE id = :id
            """), params)
            
            self.db.commit()
            
            # Return updated student
            return self.get_student_by_id(student_id)
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}")
    
    def soft_delete_student(self, student_id: int) -> bool:
        """Soft delete a student (set is_active=False)."""
        # Check if student exists
        existing = self.get_student_by_id(student_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")
        
        try:
            self.db.execute(text("""
                UPDATE students 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"id": student_id})
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Erreur lors de la suppression: {str(e)}")

def import_students_csv(self, content: bytes) -> StudentImportResponse:
    """Import students from CSV content (bytes)."""
    try:
        # Decode bytes → text (handle BOM if present)
        csv_text = content.decode("utf-8-sig")

        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_text))

        # Validate required columns
        required_columns = {"matricule", "nom", "prenom"}
        if not csv_reader.fieldnames or not required_columns.issubset(set(csv_reader.fieldnames)):
            missing = required_columns - set(csv_reader.fieldnames or [])
            raise HTTPException(
                status_code=400,
                detail=f"Colonnes manquantes dans le CSV: {', '.join(missing)}"
            )

        success_count = 0
        error_count = 0
        errors: List[str] = []

        # Process each row
        for row_num, row in enumerate(csv_reader, start=2):  # header is row 1
            try:
                # Validate row data
                student_row = StudentImportRow(
                    matricule=row["matricule"],
                    nom=row["nom"],
                    prenom=row["prenom"],
                )

                # Check duplicates
                if self.get_student_by_matricule(student_row.matricule):
                    error_count += 1
                    errors.append(f"Ligne {row_num}: Matricule '{student_row.matricule}' existe déjà")
                    continue

                # Create student
                student_data = StudentCreate(
                    matricule=student_row.matricule,
                    nom=student_row.nom,
                    prenom=student_row.prenom,
                    is_active=True,
                )
                self.create_student(student_data)
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Ligne {row_num}: {str(e)}")

        return StudentImportResponse(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            message=f"Import terminé: {success_count} étudiants créés, {error_count} erreurs",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de l'import: {str(e)}")
