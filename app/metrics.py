from fastapi import APIRouter
from starlette.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter

router = APIRouter()

# you can import these in main to increment
PRESENCE_REQUESTS = Counter("presence_requests_total", "Presence requests received")
PRESENCE_SUCCESSES = Counter("presence_success_total", "Successful presence checks")


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
