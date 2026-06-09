"""
api.py — CanIBuild FastAPI backend

Endpoints:
  POST /check  — run agent on address + mode + intent
  GET  /health — liveness probe
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.agent.agent import run

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="CanIBuild API", version="0.1.0")
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
    mode: Mode
    intent: Intent


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/check")
@limiter.limit("10/hour;3/minute")
def check(request: Request, req: CheckRequest):
    try:
        result = run(req.address, req.mode, req.intent)
        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
