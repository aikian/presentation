from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import analysis, auth, history, slides

app = FastAPI(title="PresentationCoach Presentation Analyzer")


@app.on_event("startup")
def on_startup():
    upload_path = Path(settings.upload_dir)
    if upload_path.exists():
        for f in upload_path.iterdir():
            if f.is_file():
                f.unlink(missing_ok=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.static_dir).mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(slides.router, prefix="/api/slides", tags=["slides"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(history.router, prefix="/api/history", tags=["history"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
