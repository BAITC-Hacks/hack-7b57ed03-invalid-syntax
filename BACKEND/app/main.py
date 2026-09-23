from contextlib import asynccontextmanager
import shutil
from pathlib import Path
import importlib.util

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import export, meetings, participants, tasks
from app.core.config import settings
from app.core.database import init_db
from app.ai.model_manager import model_manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    model_manager.release()


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

WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def web_app():
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/health", tags=["system"])
def health():
    device = settings.device
    if device == "auto":
        # Health must stay cheap; actual providers perform their own auto-selection.
        device = "cpu"
    configured_ffmpeg = Path(settings.ffmpeg_path).is_file() if settings.ffmpeg_path else False
    dependencies = {
        "openai": importlib.util.find_spec("openai") is not None,
        "stt": importlib.util.find_spec("faster_whisper") is not None,
        "diarization": importlib.util.find_spec("pyannote") is not None,
        "llm": importlib.util.find_spec("llama_cpp") is not None,
    }
    return {
        "status": "ok",
        "mode": "real_ai" if settings.ai_mode == "openai" else ("local_ai" if settings.ai_mode == "local" else "demo"),
        "offline": settings.ai_mode != "openai",
        "mock_mode": settings.ai_mode == "demo",
        "api_key_configured": bool(settings.openai_api_key),
        "ffmpeg": bool(configured_ffmpeg or shutil.which("ffmpeg")),
        "device": device,
        "models": {
            "stt": settings.stt_model_available and dependencies["stt"],
            "diarization": settings.diarization_model_available and dependencies["diarization"],
            "llm": settings.llm_model_path is not None and dependencies["llm"],
        },
        "dependencies": dependencies,
    }

