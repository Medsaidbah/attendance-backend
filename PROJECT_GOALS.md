Goal: MVP attendance validating students inside the campus polygon during three windows (entry/break/exit), with automatic events + 1-tap manual fallback.

Non-negotiables:
- Server truth = ST_Contains(polygon, point) + active window + tolerance.
- Tech: FastAPI + PostgreSQL/PostGIS. No Supabase/Firebase.
- Admin Web (later): React + Leaflet for polygon & windows.
- Flutter app (Android+iOS) with native bridges (Android Geofence; iOS Region Monitoring + Significant Change).
- Security: JWT, device binding 1:1, mock-location detection (Android), audit logs.

Out of scope (MVP): room-level accuracy, beacons, SSO.
