from fastapi import APIRouter
from app.api.v1.endpoints import chat, metrics

api_router = APIRouter()
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(metrics.router, tags=["metrics"])
