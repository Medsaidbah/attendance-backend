"""FastAPI application with attendance endpoints."""
from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import json
from datetime import datetime

from db import get_db
from schemas import (
    GeofenceCreate, GeofenceResponse, 
    TimeWindowCreate, TimeWindowResponse,
    PresenceCheckRequest, PresenceCheckResponse,
    LoginRequest, LoginResponse,
    StatusEnum
)
from students.routes import router as students_router
from events.routes import router as events_router
from events.service import EventService
from events.schemas import DailyStatsResponse
from auth import authenticate_user, create_access_token, get_current_user
from settings import settings
from geo import (
    check_point_in_geofence, get_active_geofence_for_point,
    get_active_time_window, geojson_to_postgis_polygon
)




app = FastAPI(
    title="Attendance Backend",
    description="API de gestion de présence avec géolocalisation",
    version="1.0.0"
)

# Include routers
app.include_router(students_router)
app.include_router(events_router)

# Auth endpoints
@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": request.username})
    return LoginResponse(
        access_token=access_token,
        token_type="bearer"
    )

# Geofence endpoints
@app.post("/geofence", response_model=GeofenceResponse)
async def upsert_geofence(geofence: GeofenceCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Upsert geofence (create or update)."""
    try:
        # Convert GeoJSON to PostGIS WKT
        wkt_polygon = geojson_to_postgis_polygon(geofence.polygon)
        
        # Check if geofence with same name exists
        existing = db.execute(text("""
            SELECT id FROM geofences WHERE name = :name
        """), {"name": geofence.name}).fetchone()
        
        if existing:
            # Update existing
            db.execute(text("""
                UPDATE geofences 
                SET polygon = ST_GeogFromText(:polygon),
                    margin_m = :margin_m,
                    updated_at = CURRENT_TIMESTAMP
                WHERE name = :name
            """), {
                "polygon": wkt_polygon,
                "margin_m": geofence.margin_m,
                "name": geofence.name
            })
            geofence_id = existing.id
        else:
            # Insert new
            result = db.execute(text("""
                INSERT INTO geofences (name, polygon, margin_m)
                VALUES (:name, ST_GeogFromText(:polygon), :margin_m)
                RETURNING id
            """), {
                "name": geofence.name,
                "polygon": wkt_polygon,
                "margin_m": geofence.margin_m
            })
            geofence_id = result.fetchone().id
        
        db.commit()
        
        # Return the geofence
        result = db.execute(text("""
            SELECT id, name, ST_AsGeoJSON(polygon) as polygon, 
                   margin_m, is_active, created_at, updated_at
            FROM geofences WHERE id = :id
        """), {"id": geofence_id}).fetchone()
        
        return GeofenceResponse(
            id=result.id,
            name=result.name,
            polygon=json.loads(result.polygon),
            margin_m=result.margin_m,
            is_active=result.is_active,
            created_at=result.created_at.isoformat(),
            updated_at=result.updated_at.isoformat()
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la sauvegarde: {str(e)}")

@app.get("/geofence", response_model=List[GeofenceResponse])
async def get_geofences(db: Session = Depends(get_db)):
    """Get all geofences."""
    result = db.execute(text("""
        SELECT id, name, ST_AsGeoJSON(polygon) as polygon,
               margin_m, is_active, created_at, updated_at
        FROM geofences
        ORDER BY created_at DESC
    """)).fetchall()
    
    return [
        GeofenceResponse(
            id=row.id,
            name=row.name,
            polygon=json.loads(row.polygon),
            margin_m=row.margin_m,
            is_active=row.is_active,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat()
        )
        for row in result
    ]

# Time windows endpoints
@app.post("/time-windows", response_model=List[TimeWindowResponse])
async def replace_time_windows(
    time_windows: List[TimeWindowCreate], 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Replace all time windows (replace-all operation)."""
    try:
        # Delete all existing time windows
        db.execute(text("DELETE FROM time_windows"))
        
        # Insert new time windows
        for tw in time_windows:
            db.execute(text("""
                INSERT INTO time_windows (name, start_time, end_time)
                VALUES (:name, :start_time, :end_time)
            """), {
                "name": tw.name,
                "start_time": tw.start_time,
                "end_time": tw.end_time
            })
        
        db.commit()
        
        # Return all time windows
        result = db.execute(text("""
            SELECT id, name, start_time, end_time, is_active, created_at, updated_at
            FROM time_windows
            ORDER BY start_time
        """)).fetchall()
        
        return [
            TimeWindowResponse(
                id=row.id,
                name=row.name,
                start_time=row.start_time.strftime("%H:%M:%S"),
                end_time=row.end_time.strftime("%H:%M:%S"),
                is_active=row.is_active,
                created_at=row.created_at.isoformat(),
                updated_at=row.updated_at.isoformat()
            )
            for row in result
        ]
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la sauvegarde: {str(e)}")

@app.get("/time-windows", response_model=List[TimeWindowResponse])
async def get_time_windows(db: Session = Depends(get_db)):
    """Get all time windows."""
    result = db.execute(text("""
        SELECT id, name, start_time, end_time, is_active, created_at, updated_at
        FROM time_windows
        ORDER BY start_time
    """)).fetchall()
    
    return [
        TimeWindowResponse(
            id=row.id,
            name=row.name,
            start_time=row.start_time.strftime("%H:%M:%S"),
            end_time=row.end_time.strftime("%H:%M:%S"),
            is_active=row.is_active,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat()
        )
        for row in result
    ]

# Presence check endpoint
@app.post("/presence/check", response_model=PresenceCheckResponse)
async def check_presence(request: PresenceCheckRequest, db: Session = Depends(get_db)):
    """Check student presence based on location and time window."""
    try:
        # Get student ID
        student = db.execute(text("""
            SELECT id FROM students WHERE matricule = :matricule
        """), {"matricule": request.matricule}).fetchone()
        
        if not student:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")
        
        student_id = student.id
        
        # Get active time window
        time_window = get_active_time_window(db)
        if not time_window:
            return PresenceCheckResponse(
                status=StatusEnum.absent,
                message="Aucune fenêtre horaire active"
            )
        
        time_window_id, time_window_name = time_window
        
        # Get active geofence
        geofence = get_active_geofence_for_point(db, request.lat, request.lon)
        if not geofence:
            return PresenceCheckResponse(
                status=StatusEnum.absent,
                message="Aucune géofence active"
            )
        
        geofence_id, geofence_name = geofence
        
        # Check if point is within geofence
        is_inside = check_point_in_geofence(db, request.lat, request.lon, geofence_id)
        
        # Determine status based on server rules
        if is_inside:
            status = StatusEnum.present
            message = "Présent dans la géofence"
        elif request.method == "manual":
            status = StatusEnum.late
            message = "En retard (vérification manuelle)"
        else:
            status = StatusEnum.outside
            message = "Absent (hors géofence)"
        
        # Record event with computed status
        event_result = db.execute(text("""
            INSERT INTO events (student_id, status, latitude, longitude, geofence_id, method)
            VALUES (:student_id, :status, :lat, :lon, :geofence_id, :method)
            RETURNING id
        """), {
            "student_id": student_id,
            "status": status.value,
            "lat": request.lat,
            "lon": request.lon,
            "geofence_id": geofence_id,
            "method": request.method
        })
        event_id = event_result.fetchone().id
        
        # Record attendance (keeping for backward compatibility)
        db.execute(text("""
            INSERT INTO attendances (student_id, event_id, time_window_id, status, geofence_id)
            VALUES (:student_id, :event_id, :time_window_id, :status, :geofence_id)
        """), {
            "student_id": student_id,
            "event_id": event_id,
            "time_window_id": time_window_id,
            "status": status.value,
            "geofence_id": geofence_id
        })
        
        db.commit()
        
        return PresenceCheckResponse(
            status=status,
            message=message,
            time_window=time_window_name,
            geofence=geofence_name,
            event_id=event_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la vérification: {str(e)}")

# Stats endpoint
@app.get("/stats/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    date: str = Query(..., description="Date pour les statistiques (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Récupérer les statistiques quotidiennes pour une date donnée."""
    from datetime import datetime
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD")
    
    service = EventService(db)
    return service.get_daily_stats(target_date)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "API de gestion de présence", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

