"""Unit tests for student import functionality."""

import pytest
import csv
import io
from unittest.mock import Mock, AsyncMock
from fastapi import UploadFile

from students.schemas import StudentImportRow
from .service import StudentService


class TestStudentImport:
    """Test cases for student import functionality."""

    def test_validate_csv_row_valid(self):
        """Test validation of valid CSV row."""
        row_data = {"matricule": "STU001", "nom": "Dupont", "prenom": "Jean"}

        student_row = StudentImportRow(**row_data)

        assert student_row.matricule == "STU001"
        assert student_row.nom == "Dupont"
        assert student_row.prenom == "Jean"

    def test_validate_csv_row_matricule_uppercase(self):
        """Test that matricule is converted to uppercase."""
        row_data = {"matricule": "stu001", "nom": "Dupont", "prenom": "Jean"}

        student_row = StudentImportRow(**row_data)
        assert student_row.matricule == "STU001"

    def test_validate_csv_row_names_title_case(self):
        """Test that names are converted to title case."""
        row_data = {"matricule": "STU001", "nom": "dupont", "prenom": "jean-pierre"}

        student_row = StudentImportRow(**row_data)
        assert student_row.nom == "Dupont"
        assert student_row.prenom == "Jean-Pierre"

    def test_validate_csv_row_trim_whitespace(self):
        """Test that whitespace is trimmed from fields."""
        row_data = {
            "matricule": "  STU001  ",
            "nom": "  Dupont  ",
            "prenom": "  Jean  ",
        }

        student_row = StudentImportRow(**row_data)
        assert student_row.matricule == "STU001"
        assert student_row.nom == "Dupont"
        assert student_row.prenom == "Jean"

    def test_validate_csv_row_empty_matricule(self):
        """Test validation fails for empty matricule."""
        row_data = {"matricule": "", "nom": "Dupont", "prenom": "Jean"}

        with pytest.raises(ValueError, match="Le matricule ne peut pas être vide"):
            StudentImportRow(**row_data)

    def test_validate_csv_row_empty_nom(self):
        """Test validation fails for empty nom."""
        row_data = {"matricule": "STU001", "nom": "", "prenom": "Jean"}

        with pytest.raises(
            ValueError, match="Le nom et prénom ne peuvent pas être vides"
        ):
            StudentImportRow(**row_data)

    def test_validate_csv_row_empty_prenom(self):
        """Test validation fails for empty prenom."""
        row_data = {"matricule": "STU001", "nom": "Dupont", "prenom": ""}

        with pytest.raises(
            ValueError, match="Le nom et prénom ne peuvent pas être vides"
        ):
            StudentImportRow(**row_data)

    def test_validate_csv_row_whitespace_only(self):
        """Test validation fails for whitespace-only fields."""
        row_data = {"matricule": "   ", "nom": "Dupont", "prenom": "Jean"}

        with pytest.raises(ValueError, match="Le matricule ne peut pas être vide"):
            StudentImportRow(**row_data)

    @pytest.mark.asyncio
    async def test_import_csv_valid_file(self):
        """Test importing a valid CSV file."""
        # Create mock CSV content
        csv_content = "matricule,nom,prenom\nSTU001,Dupont,Jean\nSTU002,Martin,Marie"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "students.csv"
        mock_file.read.return_value = csv_content.encode("utf-8")

        # Create mock database session
        mock_db = Mock()

        # Create service instance
        service = StudentService(mock_db)

        # Mock the get_student_by_matricule method to return None (no existing students)
        service.get_student_by_matricule = Mock(return_value=None)

        # Mock the create_student method
        service.create_student = Mock(
            return_value={
                "id": 1,
                "matricule": "STU001",
                "nom": "Dupont",
                "prenom": "Jean",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
        )

        # Test import
        result = await service.import_students_csv(mock_file)

        # Assertions
        assert result.success_count == 2
        assert result.error_count == 0
        assert len(result.errors) == 0
        assert "2 étudiants créés" in result.message

    @pytest.mark.asyncio
    async def test_import_csv_missing_columns(self):
        """Test importing CSV with missing columns."""
        # Create mock CSV content with missing columns
        csv_content = "matricule,nom\nSTU001,Dupont"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "students.csv"
        mock_file.read.return_value = csv_content.encode("utf-8")

        # Create mock database session
        mock_db = Mock()

        # Create service instance
        service = StudentService(mock_db)

        # Test import should raise HTTPException
        with pytest.raises(Exception, match="Colonnes manquantes"):
            await service.import_students_csv(mock_file)

    @pytest.mark.asyncio
    async def test_import_csv_duplicate_matricule(self):
        """Test importing CSV with duplicate matricule."""
        # Create mock CSV content
        csv_content = "matricule,nom,prenom\nSTU001,Dupont,Jean\nSTU001,Martin,Marie"

        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "students.csv"
        mock_file.read.return_value = csv_content.encode("utf-8")

        # Create mock database session
        mock_db = Mock()

        # Create service instance
        service = StudentService(mock_db)

        # Mock the get_student_by_matricule method
        def mock_get_student(matricule):
            if matricule == "STU001":
                return {
                    "id": 1,
                    "matricule": "STU001",
                    "nom": "Dupont",
                    "prenom": "Jean",
                }
            return None

        service.get_student_by_matricule = Mock(side_effect=mock_get_student)
        service.create_student = Mock()

        # Test import
        result = await service.import_students_csv(mock_file)

        # Assertions
        assert result.success_count == 0
        assert result.error_count == 2
        assert len(result.errors) == 2
        assert "existe déjà" in result.errors[0]
        assert "existe déjà" in result.errors[1]

    @pytest.mark.asyncio
    async def test_import_csv_invalid_file_extension(self):
        """Test importing file with invalid extension."""
        # Create mock file
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "students.txt"

        # Create mock database session
        mock_db = Mock()

        # Create service instance
        service = StudentService(mock_db)

        # Test import should raise HTTPException
        with pytest.raises(Exception, match="Le fichier doit être un CSV"):
            await service.import_students_csv(mock_file)

    def test_csv_parser_basic(self):
        """Test basic CSV parsing functionality."""
        csv_content = "matricule,nom,prenom\nSTU001,Dupont,Jean\nSTU002,Martin,Marie"
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        rows = list(csv_reader)
        assert len(rows) == 2
        assert rows[0]["matricule"] == "STU001"
        assert rows[0]["nom"] == "Dupont"
        assert rows[0]["prenom"] == "Jean"
        assert rows[1]["matricule"] == "STU002"
        assert rows[1]["nom"] == "Martin"
        assert rows[1]["prenom"] == "Marie"
