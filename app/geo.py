"""Geospatial utilities for PostGIS operations."""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, Tuple
import json

def create_point_geography(lat: float, lon: float) -> str:
    """Create PostGIS geography point from lat/lon."""
    return f"ST_GeogFromText('POINT({lon} {lat})')"

def check_point_in_geofence(db: Session, lat: float, lon: float, geofence_id: int) -> bool:
    """Check if point is within geofence using PostGIS ST_Contains."""
    query = text("""
        SELECT ST_Contains(
            polygon,
            ST_GeogFromText(:point)
        ) as contains
        FROM geofences 
        WHERE id = :geofence_id AND is_active = true
    """)
    
    result = db.execute(query, {
        "point": f"POINT({lon} {lat})",
        "geofence_id": geofence_id
    }).fetchone()
    
    return result.contains if result else False

def get_active_geofence(db: Session) -> Optional[Tuple[int, str]]:
    """Get the active geofence (assuming single campus)."""
    query = text("""
        SELECT id, name 
        FROM geofences 
        WHERE is_active = true 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = db.execute(query).fetchone()
    return (result.id, result.name) if result else None

def get_active_time_window(db: Session) -> Optional[Tuple[int, str]]:
    """Get the currently active time window based on current time."""
    query = text("""
        SELECT id, name 
        FROM time_windows 
        WHERE is_active = true 
        AND CURRENT_TIME BETWEEN start_time AND end_time
        ORDER BY start_time
        LIMIT 1
    """)
    
    result = db.execute(query).fetchone()
    return (result.id, result.name) if result else None

def geojson_to_postgis_polygon(geojson: dict) -> str:
    """Convert GeoJSON polygon to PostGIS WKT format."""
    if geojson.get("type") != "Polygon":
        raise ValueError("GeoJSON must be of type Polygon")
    
    coordinates = geojson["coordinates"][0]  # First ring (exterior)
    wkt_coords = ", ".join([f"{lon} {lat}" for lon, lat in coordinates])
    return f"POLYGON(({wkt_coords}))"




