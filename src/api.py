"""
api.py — CanIBuild FastAPI backend

Endpoints:
  POST /check   — run agent on address + pre-resolved coords + mode + intent
  GET  /suggest — address autocomplete via theLIST (layer 7)
  GET  /health  — liveness probe
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.agent.agent import run
from src.tools.geocoder import suggest_addresses

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="CanIBuild API", version="0.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Mode   = Literal["buyer", "construction", "da_owner"]
Intent = Literal["just_checking", "granny_flat", "extension", "additional_storey", "new_dwelling", "outbuilding"]


class CheckRequest(BaseModel):
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    pid: Optional[int] = None
    mode: Mode
    intent: Intent


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/suggest")
@limiter.limit("30/minute")
def suggest(request: Request, q: str = ""):
    """
    Address autocomplete — returns up to 8 real theLIST address candidates.

    Query param: q (partial address, min ~3 chars)
    Returns: [{address, pid, lat, lng}]
    """
    try:
        results = suggest_addresses(q)
        return results
    except Exception:
        return []


@app.post("/check")
@limiter.limit("10/hour;3/minute")
def check(request: Request, req: CheckRequest):
    try:
        result = run(
            address=req.address,
            mode=req.mode,
            intent=req.intent,
            lat=req.lat,
            lng=req.lng,
            pid=req.pid,
        )
        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
