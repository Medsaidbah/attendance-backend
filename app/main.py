"""FastAPI application with attendance endpoints."""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import json

# local modules (same folder as main.py inside the container)
from metrics import router as metrics_router, PRESENCE_REQUESTS, PRESENCE_SUCCESSES
from live import router as live_router
from security_hmac import hmac_guard

from db import get_db
from schemas import (
    GeofenceCreate,
    GeofenceResponse,
    TimeWindowCreate,
    TimeWindowResponse,
    PresenceCheckRequest,
    PresenceCheckResponse,
    LoginRequest,
    LoginResponse,
    StatusEnum,
)
from students.routes import router as students_router
from events.routes import router as events_router
from events.service import EventService
from events.schemas import DailyStatsResponse
from auth import authenticate_user, create_access_token, get_current_user
from geo import (
    check_point_in_geofence,
    get_active_geofence_for_point,
    get_active_time_window,
    geojson_to_postgis_polygon,
)

app = FastAPI(
    title="Attendance Backend",
    description="API de gestion de présence avec géolocalisation",
    version="1.0.0",
)

# Observability & live stream
app.include_router(metrics_router)  # exposes GET /metrics
app.include_router(live_router)  # exposes GET /stream/live

# Functional routers
app.include_router(students_router)
app.include_router(events_router)


# --------------------
# Auth
# --------------------
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
    return LoginResponse(access_token=access_token, token_type="bearer")


# --------------------
# Geofences
# --------------------
@app.post("/geofence", response_model=GeofenceResponse)
async def upsert_geofence(
    geofence: GeofenceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upsert geofence (create or update)."""
    try:
        wkt_polygon = geojson_to_postgis_polygon(geofence.polygon)
        existing = db.execute(
            text("SELECT id FROM geofences WHERE name = :name"),
            {"name": geofence.name},
        ).fetchone()

        if existing:
            db.execute(
                text(
                    """
                    UPDATE geofences 
                       SET polygon = ST_GeogFromText(:polygon),
                           margin_m = :margin_m,
                           updated_at = CURRENT_TIMESTAMP
                     WHERE name = :name
                    """
                ),
                {
                    "polygon": wkt_polygon,
                    "margin_m": geofence.margin_m,
                    "name": geofence.name,
                },
            )
            geofence_id = existing.id
        else:
            result = db.execute(
                text(
                    """
                    INSERT INTO geofences (name, polygon, margin_m)
                    VALUES (:name, ST_GeogFromText(:polygon), :margin_m)
                    RETURNING id
                    """
                ),
                {
                    "name": geofence.name,
                    "polygon": wkt_polygon,
                    "margin_m": geofence.margin_m,
                },
            )
            geofence_id = result.fetchone().id

        db.commit()

        row = db.execute(
            text(
                """
                SELECT id, name, ST_AsGeoJSON(polygon) AS polygon, 
                       margin_m, is_active, created_at, updated_at
                  FROM geofences WHERE id = :id
                """
            ),
            {"id": geofence_id},
        ).fetchone()

        return GeofenceResponse(
            id=row.id,
            name=row.name,
            polygon=json.loads(row.polygon),
            margin_m=row.margin_m,
            is_active=row.is_active,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )


@app.get("/geofence", response_model=List[GeofenceResponse])
async def get_geofences(db: Session = Depends(get_db)):
    """Get all geofences."""
    rows = db.execute(
        text(
            """
            SELECT id, name, ST_AsGeoJSON(polygon) AS polygon,
                   margin_m, is_active, created_at, updated_at
              FROM geofences
             ORDER BY created_at DESC
            """
        )
    ).fetchall()

    return [
        GeofenceResponse(
            id=r.id,
            name=r.name,
            polygon=json.loads(r.polygon),
            margin_m=r.margin_m,
            is_active=r.is_active,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]


# --------------------
# Time windows
# --------------------
@app.post("/time-windows", response_model=List[TimeWindowResponse])
async def replace_time_windows(
    time_windows: List[TimeWindowCreate],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Replace all time windows (replace-all operation)."""
    try:
        db.execute(text("DELETE FROM time_windows"))
        for tw in time_windows:
            db.execute(
                text(
                    """
                    INSERT INTO time_windows (name, start_time, end_time)
                    VALUES (:name, :start_time, :end_time)
                    """
                ),
                {"name": tw.name, "start_time": tw.start_time, "end_time": tw.end_time},
            )
        db.commit()

        rows = db.execute(
            text(
                """
                SELECT id, name, start_time, end_time, is_active, created_at, updated_at
                  FROM time_windows
                 ORDER BY start_time
                """
            )
        ).fetchall()

        return [
            TimeWindowResponse(
                id=r.id,
                name=r.name,
                start_time=r.start_time.strftime("%H:%M:%S"),
                end_time=r.end_time.strftime("%H:%M:%S"),
                is_active=r.is_active,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
            )
            for r in rows
        ]

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )


@app.get("/time-windows", response_model=List[TimeWindowResponse])
async def get_time_windows(db: Session = Depends(get_db)):
    """Get all time windows."""
    rows = db.execute(
        text(
            """
            SELECT id, name, start_time, end_time, is_active, created_at, updated_at
              FROM time_windows
             ORDER BY start_time
            """
        )
    ).fetchall()

    return [
        TimeWindowResponse(
            id=r.id,
            name=r.name,
            start_time=r.start_time.strftime("%H:%M:%S"),
            end_time=r.end_time.strftime("%H:%M:%S"),
            is_active=r.is_active,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]


# --------------------
# Presence check (HMAC-protected for mobile)
# --------------------
@app.post("/presence/check", response_model=PresenceCheckResponse)
async def check_presence(
    request: PresenceCheckRequest,
    db: Session = Depends(get_db),
    _sec: bool = Depends(hmac_guard),
):
    """Check student presence based on location and time window."""
    # increment counters on each request (not at import time)
    try:
        PRESENCE_REQUESTS.inc()
    except Exception:
        pass

    try:
        # student
        student = db.execute(
            text("SELECT id FROM students WHERE matricule = :m"),
            {"m": request.matricule},
        ).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Étudiant non trouvé")
        student_id = student.id

        # time window (server time)
        time_window = get_active_time_window(db)
        if not time_window:
            return PresenceCheckResponse(
                status=StatusEnum.absent, message="Aucune fenêtre horaire active"
            )
        time_window_id, time_window_name = time_window

        # geofence (nearest/containing)
        geofence = get_active_geofence_for_point(db, request.lat, request.lon)
        if not geofence:
            return PresenceCheckResponse(
                status=StatusEnum.absent, message="Aucune géofence active"
            )
        geofence_id, geofence_name = geofence

        # inside?
        is_inside = check_point_in_geofence(db, request.lat, request.lon, geofence_id)

        # classification
        if is_inside:
            status_val = StatusEnum.present
            message = "Présent dans la géofence"
        elif request.method == "manual":
            status_val = StatusEnum.late
            message = "En retard (vérification manuelle)"
        else:
            status_val = StatusEnum.outside
            message = "Absent (hors géofence)"

        # audit event (your current schema)
        ev = db.execute(
            text(
                """
                INSERT INTO events (student_id, status, latitude, longitude, geofence_id, method)
                VALUES (:sid, :status, :lat, :lon, :gid, :method)
                RETURNING id
                """
            ),
            {
                "sid": student_id,
                "status": status_val.value,
                "lat": request.lat,
                "lon": request.lon,
                "gid": geofence_id,
                "method": request.method,
            },
        ).fetchone()
        event_id = ev.id

        # (legacy) attendance record
        db.execute(
            text(
                """
                INSERT INTO attendances (student_id, event_id, time_window_id, status, geofence_id)
                VALUES (:sid, :eid, :twid, :status, :gid)
                """
            ),
            {
                "sid": student_id,
                "eid": event_id,
                "twid": time_window_id,
                "status": status_val.value,
                "gid": geofence_id,
            },
        )

        db.commit()

        try:
            PRESENCE_SUCCESSES.inc()
        except Exception:
            pass

        return PresenceCheckResponse(
            status=status_val,
            message=message,
            time_window=time_window_name,
            geofence=geofence_name,
            event_id=event_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erreur lors de la vérification: {str(e)}"
        )


# --------------------
# Stats
# --------------------
@app.get("/stats/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    date: str = Query(..., description="Date pour les statistiques (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Récupérer les statistiques quotidiennes pour une date donnée."""
    from datetime import datetime

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Format de date invalide. Utilisez YYYY-MM-DD"
        )
    service = EventService(db)
    return service.get_daily_stats(target_date)


# --------------------
# Root
# --------------------
@app.get("/")
async def root():
    return {"message": "API de gestion de présence", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
