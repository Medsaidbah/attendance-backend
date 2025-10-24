#!/usr/bin/env python3
"""
HMAC-based ingestion guard for mobile clients.

Headers expected:
- x-api-key: public key / key id
- x-device-id: device identifier
- x-ts: ISO8601 UTC timestamp
- x-signature: hex HMAC-SHA256 over f"{ts}.{raw_body}" using SIGNING_SECRET associated with x-api-key
"""
from __future__ import annotations
import os
import time
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Callable

from fastapi import Header, HTTPException, Request, status, Depends

# For simplicity this example loads a single API_KEY_APP and SIGNING_SECRET from env.
# In production you would map api_key -> secret from DB.
API_KEY_APP = os.getenv("API_KEY_APP", "example-api-key")
SIGNING_SECRET = os.getenv("SIGNING_SECRET", "replace-me-with-strong-secret")
ALLOWED_SKEW_SECONDS = int(os.getenv("HMAC_SKEW_SECONDS", "120"))  # default ±120s

def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()

def _iso8601_to_ts(iso: str) -> float:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        raise

async def hmac_guard(
    request: Request,
    x_api_key: str = Header(None),
    x_device_id: str = Header(None),
    x_ts: str = Header(None),
    x_signature: str = Header(None),
) -> bool:
    # Basic header presence checks
    if not x_api_key or not x_device_id or not x_ts or not x_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing HMAC headers")

    # Check API key (single-key mode)
    if x_api_key != API_KEY_APP:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown API key")

    # Timestamp skew check
    try:
        ts_val = _iso8601_to_ts(x_ts)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid x-ts format")
    now = _now_ts()
    if abs(now - ts_val) > ALLOWED_SKEW_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Timestamp skew too large")

    # Read raw body (bytes) and compute signature
    body = await request.body()
    # canonical message: f"{ts}.{raw_body}"
    message = (x_ts + "." ).encode("utf-8") + body
    secret = SIGNING_SECRET.encode("utf-8")
    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()

    # constant-time compare
    if not hmac.compare_digest(expected, x_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # Attach device id / api key to request.state for downstream handlers if needed
    request.state.device_id = x_device_id
    request.state.api_key = x_api_key
    return True
