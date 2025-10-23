"""Geospatial utilities for PostGIS operations (geography)."""
from typing import Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session


def create_point_geography(lat: float, lon: float) -> str:
    """
    Return a WKT POINT string in lon/lat order.
    Use it with ST_GeogFromText(:point) in queries.
    """
    return f"POINT({lon} {lat})"


def check_point_in_geofence(db: Session, lat: float, lon: float, geofence_id: int) -> bool:
    """
    Check if a point is inside (or within margin_m meters of) a geofence.

    Uses ST_DWithin on geography:
      - distance == 0       → strictly inside polygon
      - distance <= margin  → inside or close to boundary by margin_m meters
    """
    row = db.execute(
        text(
            """
            SELECT ST_DWithin(
                     polygon,                   -- geography polygon
                     ST_GeogFromText(:point),  -- geography point (lon lat)
                     COALESCE(margin_m, 0)     -- meters
                   ) AS inside
            FROM geofences
            WHERE id = :geofence_id
              AND is_active = true
            """
        ),
        {"point": create_point_geography(lat, lon), "geofence_id": geofence_id},
    ).fetchone()

    return bool(row and row.inside)


def get_active_geofence(db: Session) -> Optional[Tuple[int, str]]:
    """Get the latest active geofence (single selection)."""
    row = db.execute(
        text(
            """
            SELECT id, name
            FROM geofences
            WHERE is_active = true
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    ).fetchone()
    return (row.id, row.name) if row else None


def get_active_geofence_for_point(db: Session, lat: float, lon: float) -> Optional[Tuple[int, str]]:
    """
    Pick the active geofence that contains the point (or the nearest if none contains it).

    1) Prefer a polygon that contains the point (ST_DWithin with 0m on geography).
    2) Otherwise choose the nearest active polygon by edge distance.
    """
    point = create_point_geography(lat, lon)

    # 1) contains (distance == 0)
    inside = db.execute(
        text(
            """
            SELECT id, name
            FROM geofences
            WHERE is_active = true
              AND ST_DWithin(polygon, ST_GeogFromText(:point), 0)
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ),
        {"point": point},
    ).fetchone()
    if inside:
        return (inside.id, inside.name)

    # 2) nearest if none contains
    nearest = db.execute(
        text(
            """
            SELECT id, name
            FROM geofences
            WHERE is_active = true
            ORDER BY ST_Distance(polygon, ST_GeogFromText(:point)) ASC
            LIMIT 1
            """
        ),
        {"point": point},
    ).fetchone()

    return (nearest.id, nearest.name) if nearest else None


def get_active_time_window(db: Session) -> Optional[Tuple[int, str]]:
    """Get the currently active time window based on current server time."""
    row = db.execute(
        text(
            """
            SELECT id, name
            FROM time_windows
            WHERE is_active = true
              AND CURRENT_TIME BETWEEN start_time AND end_time
            ORDER BY start_time
            LIMIT 1
            """
        )
    ).fetchone()
    return (row.id, row.name) if row else None


def geojson_to_postgis_polygon(geojson: dict) -> str:
    """
    Convert a GeoJSON Polygon to WKT: POLYGON((lon lat, ...)).
    Accepts coordinates like: { "type":"Polygon", "coordinates":[ [ [lon,lat], ... ] ] }
    Ensures the ring is closed if needed.
    """
    if geojson.get("type") != "Polygon":
        raise ValueError("GeoJSON must be of type Polygon")

    ring = geojson["coordinates"][0]  # exterior ring
    if len(ring) < 4:
        raise ValueError("Polygon ring must have at least 4 coordinates (including closure)")

    # close ring if not closed
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]

    wkt_coords = ", ".join(f"{lon} {lat}" for lon, lat in ring)
    return f"POLYGON(({wkt_coords}))"
