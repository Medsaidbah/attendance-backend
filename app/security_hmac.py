#!/usr/bin/env python3
import hmac
import hashlib
import time
from fastapi import Header, HTTPException, Request
from settings import settings  # your existing pydantic-settings

MAX_SKEW = 120  # seconds


async def hmac_guard(
    request: Request,
    x_api_key: str = Header(None),
    x_device_id: str = Header(None),
    x_ts: str = Header(None),
    x_signature: str = Header(None),
):
    if not all([x_api_key, x_device_id, x_ts, x_signature]):
        raise HTTPException(status_code=401, detail="missing auth headers")
    if x_api_key != getattr(settings, "API_KEY_APP", None):
        raise HTTPException(status_code=401, detail="invalid api key")
    try:
        ts = int(x_ts)
    except Exception:
        raise HTTPException(status_code=401, detail="bad timestamp")
    if abs(int(time.time()) - ts) > MAX_SKEW:
        raise HTTPException(status_code=401, detail="stale request")

    body = await request.body()
    msg = str(ts).encode("utf-8") + b"." + body
    secret = getattr(settings, "SIGNING_SECRET", None)
    if not secret:
        raise HTTPException(status_code=500, detail="server signing secret not set")
    want = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, x_signature):
        raise HTTPException(status_code=401, detail="bad signature")

    # expose for handler if useful
    request.state.device_id = x_device_id
    request.state.ts = ts
    return True
