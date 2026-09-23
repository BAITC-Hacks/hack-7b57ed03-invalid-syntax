from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import export, meetings, participants, tasks
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Local-first meeting transcription and protocol API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(meetings.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(participants.router, prefix=settings.api_prefix)
app.include_router(export.router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
def health():
    models_root = settings.upload_dir.parent / "models"
    return {
        "status": "ok",
        "offline": True,
        "mock_mode": settings.mock_mode,
        "device": settings.device,
        "models": {
            "stt": (models_root / "whisper").exists(),
            "diarization": (models_root / "diarization").exists(),
            "llm": (models_root / "llm").exists(),
        },
    }

