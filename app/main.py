import os
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.api.v1.router import api_router

# Initialisation de l'application FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url="/openapi.json"
)

# Configuration CORS pour autoriser les requêtes frontend/mobiles
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connexion à Redis (pour le health check et le rate limiting)
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

# Inclusion des routes v1 (/v1/chat/completions, etc.)
app.include_router(api_router, prefix="/v1")


@app.get("/")
def read_root():
    """Point d'entrée principal."""
    return {
        "status": "online",
        "message": "Passerelle LLM Intelligente opérationnelle",
        "docs": "/docs"
    }

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    """Page du tableau de bord (la clé admin se saisit dans le navigateur)."""
    return (Path(__file__).parent / "static" / "dashboard.html").read_text(encoding="utf-8")
@app.get("/health")
def health_check():
    """Vérification de la santé de l'API et de la connexion Redis."""
    try:
        redis_ping = redis_client.ping()
        return {
            "status": "healthy",
            "redis_connected": redis_ping
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis_error": str(e)
        }


main_app = app