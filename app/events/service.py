"""Business logic for events."""
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
from fastapi import HTTPException

from events.schemas import EventCreate, EventQueryParams, DailyStatsResponse, EventWithStudentResponse


class EventService:
    """Service class for event operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_event(self, event_data: EventCreate) -> Dict[str, Any]:
        """Create a new event."""
        try:
            result = self.db.execute(text("""
                INSERT INTO events (student_id, status, latitude, longitude, geofence_id, method)
                VALUES (:student_id, :status, :latitude, :longitude, :geofence_id, :method)
                RETURNING id, created_at
            """), {
                "student_id": event_data.student_id,
                "status": event_data.status.value,
                "latitude": event_data.latitude,
                "longitude": event_data.longitude,
                "geofence_id": event_data.geofence_id,
                "method": event_data.method.value
            })
            
            new_event = result.fetchone()
            self.db.commit()
            
            return {
                "id": new_event.id,
                "student_id": event_data.student_id,
                "status": event_data.status.value,
                "latitude": float(event_data.latitude),
                "longitude": float(event_data.longitude),
                "geofence_id": event_data.geofence_id,
                "method": event_data.method.value,
                "created_at": new_event.created_at
            }
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"Erreur lors de la création de l'événement: {str(e)}")
    
    def get_events(
        self, 
        matricule: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get events with filtering and pagination."""
        # Build query conditions
        conditions = []
        params = {"limit": limit, "offset": offset}
        
        if matricule:
            conditions.append("s.matricule = :matricule")
            params["matricule"] = matricule
        
        if from_date:
            conditions.append("e.created_at >= :from_date")
            params["from_date"] = from_date
        
        if to_date:
            conditions.append("e.created_at <= :to_date")
            params["to_date"] = to_date
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM events e
            JOIN students s ON e.student_id = s.id
            {where_clause}
        """
        total_result = self.db.execute(text(count_query), params).fetchone()
        total = total_result.total if total_result else 0
        
        # Get events with student and geofence information
        events_query = f"""
            SELECT 
                e.id, e.student_id, e.status, e.latitude, e.longitude, 
                e.geofence_id, e.method, e.created_at,
                s.matricule as student_matricule,
                s.nom as student_nom,
                s.prenom as student_prenom,
                g.name as geofence_name
            FROM events e
            JOIN students s ON e.student_id = s.id
            LEFT JOIN geofences g ON e.geofence_id = g.id
            {where_clause}
            ORDER BY e.created_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        events = self.db.execute(text(events_query), params).fetchall()
        
        return [
            {
                "id": event.id,
                "student_id": event.student_id,
                "status": event.status,
                "latitude": float(event.latitude),
                "longitude": float(event.longitude),
                "geofence_id": event.geofence_id,
                "method": event.method,
                "created_at": event.created_at,
                "student_matricule": event.student_matricule,
                "student_nom": event.student_nom,
                "student_prenom": event.student_prenom,
                "geofence_name": event.geofence_name
            }
            for event in events
        ], total
    
    def get_daily_stats(self, target_date: date) -> Dict[str, Any]:
        """Get daily statistics for a specific date."""
        try:
            # Get statistics for the specified date
            stats_query = """
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN status = 'present' THEN 1 END) as present_count,
                    COUNT(CASE WHEN status = 'late' THEN 1 END) as late_count,
                    COUNT(CASE WHEN status = 'absent' THEN 1 END) as absent_count,
                    COUNT(CASE WHEN status = 'outside' THEN 1 END) as outside_count,
                    COUNT(CASE WHEN method = 'manual' THEN 1 END) as manual_count,
                    COUNT(CASE WHEN method = 'auto' THEN 1 END) as auto_count
                FROM events
                WHERE DATE(created_at) = :target_date
            """
            
            result = self.db.execute(text(stats_query), {"target_date": target_date}).fetchone()
            
            if not result:
                return {
                    "date": target_date.strftime("%Y-%m-%d"),
                    "total_events": 0,
                    "present_count": 0,
                    "late_count": 0,
                    "absent_count": 0,
                    "outside_count": 0,
                    "manual_count": 0,
                    "auto_count": 0
                }
            
            return {
                "date": target_date.strftime("%Y-%m-%d"),
                "total_events": result.total_events or 0,
                "present_count": result.present_count or 0,
                "late_count": result.late_count or 0,
                "absent_count": result.absent_count or 0,
                "outside_count": result.outside_count or 0,
                "manual_count": result.manual_count or 0,
                "auto_count": result.auto_count or 0
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erreur lors de la récupération des statistiques: {str(e)}")
    
    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get event by ID with student and geofence information."""
        result = self.db.execute(text("""
            SELECT 
                e.id, e.student_id, e.status, e.latitude, e.longitude, 
                e.geofence_id, e.method, e.created_at,
                s.matricule as student_matricule,
                s.nom as student_nom,
                s.prenom as student_prenom,
                g.name as geofence_name
            FROM events e
            JOIN students s ON e.student_id = s.id
            LEFT JOIN geofences g ON e.geofence_id = g.id
            WHERE e.id = :event_id
        """), {"event_id": event_id}).fetchone()
        
        if not result:
            return None
        
        return {
            "id": result.id,
            "student_id": result.student_id,
            "status": result.status,
            "latitude": float(result.latitude),
            "longitude": float(result.longitude),
            "geofence_id": result.geofence_id,
            "method": result.method,
            "created_at": result.created_at,
            "student_matricule": result.student_matricule,
            "student_nom": result.student_nom,
            "student_prenom": result.student_prenom,
            "geofence_name": result.geofence_name
        }

