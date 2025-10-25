"""Unit tests for events functionality."""

from unittest.mock import Mock

from events.schemas import EventStatus, EventMethod, EventCreate, DailyStatsResponse
from .service import EventService


class TestEventSchemas:
    """Test cases for event schemas."""

    def test_event_status_enum(self):
        """Test event status enumeration."""
        assert EventStatus.present == "present"
        assert EventStatus.late == "late"
        assert EventStatus.absent == "absent"
        assert EventStatus.outside == "outside"

    def test_event_method_enum(self):
        """Test event method enumeration."""
        assert EventMethod.manual == "manual"
        assert EventMethod.auto == "auto"

    def test_event_create_valid(self):
        """Test valid event creation."""
        event_data = EventCreate(
            student_id=1,
            status=EventStatus.present,
            latitude=48.8566,
            longitude=2.3522,
            geofence_id=1,
            method=EventMethod.auto,
        )

        assert event_data.student_id == 1
        assert event_data.status == EventStatus.present
        assert event_data.latitude == 48.8566
        assert event_data.longitude == 2.3522
        assert event_data.geofence_id == 1
        assert event_data.method == EventMethod.auto

    def test_event_create_optional_geofence(self):
        """Test event creation with optional geofence."""
        event_data = EventCreate(
            student_id=1,
            status=EventStatus.outside,
            latitude=48.8566,
            longitude=2.3522,
            geofence_id=None,
            method=EventMethod.manual,
        )

        assert event_data.geofence_id is None
        assert event_data.status == EventStatus.outside
        assert event_data.method == EventMethod.manual


class TestEventService:
    """Test cases for event service."""

    def test_daily_stats_response(self):
        """Test daily stats response structure."""
        stats = DailyStatsResponse(
            date="2023-01-15",
            total_events=25,
            present_count=20,
            late_count=3,
            absent_count=1,
            outside_count=1,
            manual_count=5,
            auto_count=20,
        )

        assert stats.date == "2023-01-15"
        assert stats.total_events == 25
        assert stats.present_count == 20
        assert stats.late_count == 3
        assert stats.absent_count == 1
        assert stats.outside_count == 1
        assert stats.manual_count == 5
        assert stats.auto_count == 20

    def test_event_service_initialization(self):
        """Test event service initialization."""
        mock_db = Mock()
        service = EventService(mock_db)
        assert service.db == mock_db
