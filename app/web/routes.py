from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


STATIC_DIR = Path(__file__).parent / "static"


def build_web_router() -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return router


def mount_static(app) -> None:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

