"""
api.py — SiteCheck FastAPI backend

Endpoints:
  POST /check  — run agent on address + mode + intent
  GET  /health — liveness probe
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal

from src.agent.agent import run

app = FastAPI(title="SiteCheck API", version="0.1.0")

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
def check(req: CheckRequest):
    try:
        result = run(req.address, req.mode, req.intent)
        if result.get("error"):
            raise HTTPException(status_code=422, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
