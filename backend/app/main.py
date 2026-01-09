from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.services.registry import Registry
from app.routes import models, predict, evaluate

app = FastAPI(title="Prediction Server")


# --- Absolute paths ---
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent

MANIFEST_PATH = BACKEND_DIR / "artifacts" / "manifest.json"
registry = Registry(str(MANIFEST_PATH))

@app.on_event("startup")
def startup():
    registry.load()

app.state.registry = registry

app.include_router(models.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")

# --- Serve the UI from prediction-server/frontend ---
FRONTEND_DIR = PROJECT_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "status": "ok",
            "docs": "/docs",
            "models": "/api/models",
            "frontend_missing": str(FRONTEND_DIR),
        }