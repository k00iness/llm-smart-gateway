from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.models.response import MetricsResponse
from app.services.metrics import metrics_service

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse, dependencies=[Depends(require_admin)])
async def get_metrics():
    return await metrics_service.snapshot()