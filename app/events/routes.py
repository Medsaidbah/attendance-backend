"""FastAPI routes for events."""

from typing import Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import get_db
from auth import get_current_user
from events.service import EventService  # absolute import avoids confusion
from events.schemas import (
    EventListResponse,
    EventWithStudentResponse,
    DailyStatsResponse,
)

router = APIRouter(prefix="/events", tags=["events"])


# Put the fixed path BEFORE the parameterized one to avoid conflicts
@router.get("/stats/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    target_date: date = Query(
        ..., description="Date pour les statistiques (YYYY-MM-DD)"
    ),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Récupérer les statistiques quotidiennes pour une date donnée."""
    service = EventService(db)
    return service.get_daily_stats(target_date)


@router.get("", response_model=EventListResponse)
async def get_events(
    matricule: Optional[str] = Query(None, description="Matricule de l'étudiant"),
    from_date: Optional[datetime] = Query(
        None, description="Date de début (ISO format)"
    ),
    to_date: Optional[datetime] = Query(None, description="Date de fin (ISO format)"),
    limit: int = Query(50, ge=1, le=100, description="Nombre d'éléments par page"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Récupérer la liste des événements avec filtres et pagination."""
    service = EventService(db)
    events, total = service.get_events(
        matricule=matricule,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return EventListResponse(events=events, total=total, limit=limit, offset=offset)


@router.get("/{event_id}", response_model=EventWithStudentResponse)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Récupérer un événement par son ID."""
    service = EventService(db)
    event = service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return event
