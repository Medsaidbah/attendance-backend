from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio, json

router = APIRouter()

async def _stream():
    while True:
        yield f"data: {json.dumps({'alive': True})}\n\n"
        await asyncio.sleep(5)

@router.get("/stream/live")
async def stream_live():
    return StreamingResponse(_stream(), media_type="text/event-stream")
