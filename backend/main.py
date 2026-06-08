from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.clusters import router as clusters_router
from api.routes.health import router as health_router
from api.routes.investigate import router as investigate_router
from core.config import settings
from core.logging import setup_logging

setup_logging()

app = FastAPI(title="AI Kubernetes Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(clusters_router)
app.include_router(investigate_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Kubernetes Agent API"}
