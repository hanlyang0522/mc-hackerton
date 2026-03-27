"""FastAPI 서버 진입점."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .router import router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="자소서 생성기", version="0.1.0")
app.include_router(router, prefix="/api")
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
